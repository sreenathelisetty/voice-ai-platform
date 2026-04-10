"""
Whisper ASR worker.

Consumes utterance byte arrays from asr_queue,
runs Whisper transcription in a thread-pool executor,
emits transcript strings to llm_queue.
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import whisper

from app.audio.resampler import pcm_bytes_to_float32, resample
from app.config import get_settings
from app.session.models import PipelineResult
from app.utils.exceptions import ASRError
from app.utils.logging import get_logger
from app.utils.retry import async_retry

log = get_logger(__name__)

_model: whisper.Whisper | None = None
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="whisper")


def load_whisper_model() -> whisper.Whisper:
    global _model
    if _model is None:
        settings = get_settings()
        log.info("loading_whisper_model", size=settings.whisper_model_size)
        _model = whisper.load_model(
            settings.whisper_model_size,
            device=settings.whisper_device,
            download_root=settings.whisper_model_dir,
        )
        log.info("whisper_model_loaded")
    return _model


def _transcribe_sync(pcm_bytes: bytes) -> str:
    """Synchronous Whisper call — runs in thread pool."""
    settings = get_settings()
    model = load_whisper_model()

    # Convert PCM int16 → float32 and resample to 16 kHz if needed
    audio = pcm_bytes_to_float32(pcm_bytes)
    if settings.audio_input_sample_rate != 16000:
        audio = resample(audio, settings.audio_input_sample_rate, 16000)

    # Pad or trim to Whisper's expected 30s window
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    options = whisper.DecodingOptions(fp16=False, language="en")
    result = whisper.decode(model, mel, options)
    return result.text.strip()


@async_retry(max_attempts=2, base_delay=0.3, exceptions=(ASRError,))
async def transcribe(pcm_bytes: bytes) -> str:
    """Async wrapper: run Whisper in thread pool, return transcript."""
    loop = asyncio.get_running_loop()
    try:
        transcript = await loop.run_in_executor(_executor, _transcribe_sync, pcm_bytes)
        return transcript
    except Exception as exc:
        raise ASRError(str(exc)) from exc


async def asr_worker(
    asr_queue: asyncio.Queue[bytes],
    llm_queue: asyncio.Queue[tuple[str, PipelineResult] | None],
    session_id: str,
    ws_send_queue: asyncio.Queue[bytes | str | None] | None = None,
) -> None:
    """
    Long-running async task that drains the ASR queue.
    Sends (transcript, pipeline_result) tuples to the LLM queue.
    """
    log.info("asr_worker_started", session_id=session_id)
    while True:
        pcm_bytes = await asr_queue.get()
        if pcm_bytes is None:  # sentinel: shutdown
            await llm_queue.put(None)
            break

        result = PipelineResult(session_id=session_id, turn_start=time.time())
        result.asr_start = time.time()

        try:
            transcript = await transcribe(pcm_bytes)
        except ASRError as exc:
            log.error("asr_failed", session_id=session_id, error=str(exc))
            transcript = ""

        result.asr_end = time.time()
        result.transcript = transcript
        log.info("asr_complete", session_id=session_id, transcript=transcript[:80],
                 latency_ms=result.asr_latency_ms)

        if transcript:
            if ws_send_queue is not None:
                import json
                await ws_send_queue.put(json.dumps({"type": "transcript", "text": transcript}))
            await llm_queue.put((transcript, result))

        asr_queue.task_done()
