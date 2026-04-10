"""Pytest fixtures for unit and integration tests."""

from __future__ import annotations

import asyncio
import math
import struct

import fakeredis.aioredis as fake_aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ── Audio fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_pcm_audio() -> bytes:
    """1 second of 440 Hz sine wave at 16 kHz, int16 PCM."""
    sample_rate = 16000
    frequency = 440.0
    duration = 1.0
    n_samples = int(sample_rate * duration)
    samples = [
        int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
        for i in range(n_samples)
    ]
    return struct.pack(f"<{n_samples}h", *samples)


@pytest.fixture
def silence_pcm_audio() -> bytes:
    """1 second of silence at 16 kHz."""
    return b"\x00" * (16000 * 2)


# ── Redis fixture ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def mock_redis(monkeypatch):
    """Patch get_redis() to return a fakeredis instance."""
    fake = fake_aioredis.FakeRedis(decode_responses=False)
    import app.storage.redis_client as rc
    monkeypatch.setattr(rc, "_pool", fake)
    yield fake
    await fake.aclose()


# ── HTTP client fixture ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_client(mock_redis):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
