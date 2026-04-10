"""Async repository functions for turns and metrics."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MetricSnapshot, Session, Turn
from app.storage.postgres_client import get_session_factory
from app.utils.logging import get_logger

log = get_logger(__name__)


async def ensure_session(session_id: str, user_id: str | None = None, device_type: str | None = None) -> None:
    """Insert session row if it doesn't exist."""
    factory = get_session_factory()
    async with factory() as db:
        existing = await db.get(Session, session_id)
        if existing is None:
            db.add(Session(id=session_id, user_id=user_id, device_type=device_type))
            await db.commit()


async def log_turn(
    session_id: str,
    transcript: str | None,
    response_text: str | None,
    e2e_latency_ms: int | None = None,
    asr_latency_ms: int | None = None,
    llm_first_token_ms: int | None = None,
    llm_total_ms: int | None = None,
    tts_latency_ms: int | None = None,
) -> int:
    """Persist a completed turn and return its id."""
    factory = get_session_factory()
    async with factory() as db:
        turn = Turn(
            session_id=session_id,
            role="user",
            transcript=transcript,
            response_text=response_text,
            e2e_latency_ms=e2e_latency_ms,
            asr_latency_ms=asr_latency_ms,
            llm_first_token_ms=llm_first_token_ms,
            llm_total_ms=llm_total_ms,
            tts_latency_ms=tts_latency_ms,
        )
        db.add(turn)
        await db.commit()
        await db.refresh(turn)
        return turn.id


async def get_session_turns(session_id: str, limit: int = 50) -> list[Turn]:
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(Turn)
            .where(Turn.session_id == session_id)
            .order_by(Turn.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


async def compute_and_store_hourly_metrics(hour: datetime) -> None:
    """Aggregate per-turn latency for a given hour and store percentiles."""
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(Turn).where(
                Turn.timestamp >= hour,
                Turn.timestamp < hour + timedelta(hours=1),
            )
        )
        turns = list(result.scalars().all())
        if not turns:
            return

        for metric_name, values in [
            ("e2e_latency_ms", [t.e2e_latency_ms for t in turns if t.e2e_latency_ms]),
            ("asr_latency_ms", [t.asr_latency_ms for t in turns if t.asr_latency_ms]),
            ("llm_first_token_ms", [t.llm_first_token_ms for t in turns if t.llm_first_token_ms]),
        ]:
            if not values:
                continue
            arr = np.array(values)
            snapshot = MetricSnapshot(
                hour=hour,
                metric_name=metric_name,
                p50_ms=float(np.percentile(arr, 50)),
                p95_ms=float(np.percentile(arr, 95)),
                p99_ms=float(np.percentile(arr, 99)),
                sample_count=len(values),
            )
            db.add(snapshot)
        await db.commit()
