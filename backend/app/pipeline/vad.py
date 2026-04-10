"""
WebRTC VAD-based utterance segmenter.

Receives raw PCM bytes (16 kHz, 16-bit, mono) in any chunk size.
Internally processes 20ms frames and emits complete utterances
(as byte arrays) after detecting a configurable silence period.
"""

from __future__ import annotations

import asyncio

import webrtcvad

from app.config import get_settings
from app.utils.logging import get_logger

log = get_logger(__name__)

FRAME_DURATION_MS = 20   # WebRTC VAD only supports 10, 20, or 30ms
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2     # int16
FRAME_BYTES = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000) * BYTES_PER_SAMPLE  # 640


class VADProcessor:
    """
    Consume raw PCM bytes, detect utterance boundaries via VAD,
    and push complete utterances onto `output_queue`.
    """

    def __init__(self, output_queue: asyncio.Queue[bytes]) -> None:
        settings = get_settings()
        self._vad = webrtcvad.Vad(settings.vad_aggressiveness)
        self._silence_frames_needed = settings.vad_silence_frames
        self._output_queue = output_queue
        self._buffer: bytes = b""        # incomplete audio not yet framed
        self._speech_buffer: bytes = b"" # accumulated speech bytes for current utterance
        self._silence_count: int = 0     # consecutive silent frames since last speech
        self._in_speech: bool = False

    def feed(self, raw_pcm: bytes) -> None:
        """
        Feed arbitrary-length PCM bytes into the processor.
        Utterances are pushed synchronously to the queue
        (queue.put_nowait is safe if the queue is large enough).
        """
        self._buffer += raw_pcm
        while len(self._buffer) >= FRAME_BYTES:
            frame = self._buffer[:FRAME_BYTES]
            self._buffer = self._buffer[FRAME_BYTES:]
            self._process_frame(frame)

    def _process_frame(self, frame: bytes) -> None:
        try:
            is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
        except Exception as exc:
            log.warning("vad_frame_error", error=str(exc))
            is_speech = False

        if is_speech:
            self._speech_buffer += frame
            self._silence_count = 0
            self._in_speech = True
        else:
            if self._in_speech:
                self._speech_buffer += frame  # include trailing silence for naturalness
                self._silence_count += 1
                if self._silence_count >= self._silence_frames_needed:
                    self._flush_utterance()
            # If not in speech and not accumulating, just discard silence

    def _flush_utterance(self) -> None:
        if self._speech_buffer:
            utterance = self._speech_buffer
            self._speech_buffer = b""
            self._silence_count = 0
            self._in_speech = False
            try:
                self._output_queue.put_nowait(utterance)
            except asyncio.QueueFull:
                log.warning("vad_queue_full_utterance_dropped")

    def flush_remaining(self) -> None:
        """Call on WebSocket close to emit any buffered speech."""
        if self._in_speech and self._speech_buffer:
            self._flush_utterance()
