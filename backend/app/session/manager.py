"""Session lifecycle management backed by Redis."""

from __future__ import annotations

import time

from app.config import get_settings
from app.session.models import ConversationTurn, SessionState, SessionStatus
from app.storage.redis_client import (
    get_redis,
    history_key,
    pack,
    reconnect_key,
    session_key,
    unpack,
)
from app.utils.exceptions import SessionNotFoundError
from app.utils.logging import get_logger

log = get_logger(__name__)


class SessionManager:
    def __init__(self) -> None:
        self._settings = get_settings()

    async def create(
        self,
        session_id: str,
        user_id: str | None = None,
        device_type: str | None = None,
    ) -> SessionState:
        redis = await get_redis()
        state = SessionState(session_id=session_id, user_id=user_id, device_type=device_type)
        ttl = self._settings.redis_session_ttl_seconds
        await redis.setex(session_key(session_id), ttl, pack(state.model_dump()))
        log.info("session_created", session_id=session_id)
        return state

    async def get(self, session_id: str) -> SessionState:
        redis = await get_redis()
        raw = await redis.get(session_key(session_id))
        if raw is None:
            raise SessionNotFoundError(session_id)
        return SessionState(**unpack(raw))

    async def touch(self, session_id: str) -> None:
        """Reset TTL on active session."""
        redis = await get_redis()
        ttl = self._settings.redis_session_ttl_seconds
        key = session_key(session_id)
        exists = await redis.exists(key)
        if exists:
            await redis.expire(key, ttl)
            await redis.expire(history_key(session_id), ttl)

    async def update_history(self, session_id: str, turn: ConversationTurn) -> None:
        redis = await get_redis()
        max_turns = self._settings.redis_max_history_turns
        key = history_key(session_id)
        ttl = self._settings.redis_session_ttl_seconds
        # Store each turn as a msgpack blob in a Redis list
        await redis.rpush(key, pack(turn.model_dump()))
        # Keep only the last max_turns entries
        await redis.ltrim(key, -max_turns * 2, -1)  # *2 for user+assistant pairs
        await redis.expire(key, ttl)

    async def get_history(self, session_id: str) -> list[ConversationTurn]:
        redis = await get_redis()
        raw_list = await redis.lrange(history_key(session_id), 0, -1)
        return [ConversationTurn(**unpack(raw)) for raw in raw_list]

    async def mark_disconnected(self, session_id: str) -> None:
        redis = await get_redis()
        raw = await redis.get(session_key(session_id))
        if raw is None:
            return
        state = SessionState(**unpack(raw))
        state.status = SessionStatus.DISCONNECTED
        state.last_active = time.time()
        reconnect_ttl = self._settings.redis_reconnect_window_seconds
        # Keep session alive for reconnect window, then let it expire naturally
        await redis.setex(session_key(session_id), reconnect_ttl, pack(state.model_dump()))
        await redis.setex(reconnect_key(session_id), reconnect_ttl, b"1")
        log.info("session_disconnected", session_id=session_id, reconnect_window_s=reconnect_ttl)

    async def can_reconnect(self, session_id: str) -> bool:
        redis = await get_redis()
        return bool(await redis.exists(reconnect_key(session_id)))

    async def delete(self, session_id: str) -> None:
        redis = await get_redis()
        await redis.delete(
            session_key(session_id),
            history_key(session_id),
            reconnect_key(session_id),
        )
        log.info("session_deleted", session_id=session_id)
