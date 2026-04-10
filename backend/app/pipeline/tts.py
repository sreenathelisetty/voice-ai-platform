"""
Coqui TTS worker with gTTS fallback.

Consumes (sentence, pipeline_result) from tts_queue.
Synthesises each sentence, Opus-encodes it, sends binary frames over the WebSocket.
"""

from __future__ import annotations

import asyncio
import io
import time
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pydub
import soundfile as sf

from app.audio.codec import encode_pcm_to_opus
from app.audio.resampler import float32_to_pcm_bytes, resample
from app.config import get_settings
from app.session.models import PipelineResult
from app.utils.exceptions import TTSError
from app.utils.logging import get_logger
from app.utils.retry import async_retry

log = get_logger(__name__)

_tts_model = None
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="coqui-tts")


def load_tts_model():
    global _tts_model
    if _tts_model is None:
        from TTS.api import TTS
        settings = get_settings()
        log.info("loading_tts_model", model=settings.tts_model_name)
        _tts_model = TTS(
            model_name=settings.tts_model_name,
            progress_bar=False,
        )
        log.info("tts_model_loaded")
    return _tts_model


def _synthesize_coqui(text: str) -> bytes:
    """Run Coqui TTS synchronously; returns WAV bytes."""
    settings = get_settings()
    model = load_tts_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        model.tts_to_file(text=text, file_path=tmp_path)
        audio, sr = sf.read(tmp_path, dtype="float32")
        if sr != settings.tts_output_sample_rate:
            audio = resample(audio, sr, settings.tts_output_sample_rate)
        return float32_to_pcm_bytes(audio)
    finally:
        os.unlink(tmp_path)


def _synthesize_gtts_fallback(text: str) -> bytes:
    """gTTS fallback; returns PCM bytes at 24 kHz."""
    from gtts import gTTS
    settings = get_settings()
    buf = io.BytesIO()
    tts = gTTS(text=text, lang="en")
    tts.write_to_fp(buf)
    buf.seek(0)
    audio_seg = pydub.AudioSegment.from_mp3(buf)
    audio_seg = audio_seg.set_frame_rate(settings.tts_output_sample_rate).set_channels(1)
    return audio_seg.raw_data


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int, channels: int = 1) -> bytes:
    """Wrap raw int16 PCM bytes in a WAV container."""
    import struct
    data_size = len(pcm_bytes)
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
                          sample_rate * channels * 2, channels * 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_bytes)
    return buf.getvalue()


@async_retry(max_attempts=2, base_delay=0.3, exceptions=(TTSError,))
async def synthesize(text: str) -> bytes:
    """Async TTS: try Coqui, fall back to gTTS."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(_executor, _synthesize_coqui, text)
    except Exception as coqui_exc:
        log.warning("coqui_tts_failed_using_fallback", error=str(coqui_exc))
        try:
            return await loop.run_in_executor(_executor, _synthesize_gtts_fallback, text)
        except Exception as fallback_exc:
            raise TTSError(str(fallback_exc)) from fallback_exc


async def tts_worker(
    tts_queue: asyncio.Queue[tuple[str, PipelineResult] | None],
    ws_send: asyncio.Queue[bytes],
    session_id: str,
) -> None:
    """Long-running async task: synthesise sentences and push Opus frames to ws_send queue."""
    log.info("tts_worker_started", session_id=session_id)

    while True:
        item = await tts_queue.get()
        if item is None:  # sentinel
            await ws_send.put(None)
            break

        sentence, result = item
        result.tts_start = time.time()

        try:
            pcm_bytes = await synthesize(sentence)
        except TTSError as exc:
            log.error("tts_failed", session_id=session_id, error=str(exc))
            tts_queue.task_done()
            continue

        result.tts_end = time.time()

        # Send as a single WAV frame so any client (browser, mobile) can decode it
        settings = get_settings()
        wav_bytes = _pcm_to_wav(pcm_bytes, settings.tts_output_sample_rate)
        await ws_send.put(wav_bytes)

        log.info("tts_complete", session_id=session_id,
                 sentence_len=len(sentence), latency_ms=result.tts_latency_ms)

        tts_queue.task_done()
