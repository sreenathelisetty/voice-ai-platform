"""
Async Redis connection pool and key-schema helpers.
Uses msgpack for compact session serialisation.
"""

from __future__ import annotations

import msgpack
import redis.asyncio as aioredis

from app.config import get_settings
from app.utils.logging import get_logger

log = get_logger(__name__)

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=False,  # we handle bytes ourselves via msgpack
            max_connections=50,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Verify connectivity
        await _pool.ping()
        log.info("redis_connected", url=settings.redis_url)
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        log.info("redis_closed")


# ── Key schema ────────────────────────────────────────────────────────────────

def session_key(session_id: str) -> str:
    return f"session:{session_id}"


def history_key(session_id: str) -> str:
    return f"history:{session_id}"


def reconnect_key(session_id: str) -> str:
    return f"reconnect:{session_id}"


# ── Serialisation helpers ─────────────────────────────────────────────────────

def pack(data: dict) -> bytes:
    return msgpack.packb(data, use_bin_type=True)


def unpack(data: bytes) -> dict:
    return msgpack.unpackb(data, raw=False)
