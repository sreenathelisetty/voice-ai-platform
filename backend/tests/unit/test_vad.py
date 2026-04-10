"""VAD frame segmentation unit tests."""

import asyncio
import math
import struct

import pytest

from app.pipeline.vad import VADProcessor


def make_pcm(duration_ms: int, frequency: float = 440.0, sample_rate: int = 16000) -> bytes:
    n = int(sample_rate * duration_ms / 1000)
    samples = [int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate)) for i in range(n)]
    return struct.pack(f"<{n}h", *samples)


def make_silence(duration_ms: int, sample_rate: int = 16000) -> bytes:
    n = int(sample_rate * duration_ms / 1000)
    return b"\x00" * (n * 2)


@pytest.mark.asyncio
async def test_silence_only_produces_no_utterances():
    q: asyncio.Queue[bytes] = asyncio.Queue()
    vad = VADProcessor(q)
    vad.feed(make_silence(3000))
    vad.flush_remaining()
    assert q.empty()


@pytest.mark.asyncio
async def test_speech_then_silence_produces_one_utterance():
    q: asyncio.Queue[bytes] = asyncio.Queue()
    vad = VADProcessor(q)
    vad.feed(make_pcm(500))         # 500ms of speech
    vad.feed(make_silence(1000))    # 1s of silence (triggers flush)
    assert not q.empty()
    utterance = await q.get()
    assert isinstance(utterance, bytes)
    assert len(utterance) > 0


@pytest.mark.asyncio
async def test_flush_remaining_emits_buffered_speech():
    q: asyncio.Queue[bytes] = asyncio.Queue()
    vad = VADProcessor(q)
    vad.feed(make_pcm(300))         # speech without trailing silence
    assert q.empty()
    vad.flush_remaining()
    assert not q.empty()
