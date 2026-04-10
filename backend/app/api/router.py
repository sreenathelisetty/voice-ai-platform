"""REST API routes: health, sessions, metrics."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.repository import get_session_turns
from app.metrics.collector import MetricsCollector
from app.session.manager import SessionManager
from app.storage.postgres_client import check_db_health
from app.storage.redis_client import get_redis
from app.utils.exceptions import SessionNotFoundError

router = APIRouter()
session_manager = SessionManager()


class HealthResponse(BaseModel):
    status: str
    redis: bool
    postgres: bool


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    redis_ok = True
    try:
        r = await get_redis()
        await r.ping()
    except Exception:
        redis_ok = False

    pg_ok = await check_db_health()

    status = "ok" if (redis_ok and pg_ok) else "degraded"
    return HealthResponse(status=status, redis=redis_ok, postgres=pg_ok)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    try:
        state = await session_manager.get(session_id)
        return state.model_dump()
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions/{session_id}/turns")
async def get_turns(session_id: str, limit: int = 20) -> list:
    turns = await get_session_turns(session_id, limit=limit)
    return [
        {
            "id": t.id,
            "transcript": t.transcript,
            "response_text": t.response_text,
            "e2e_latency_ms": t.e2e_latency_ms,
            "asr_latency_ms": t.asr_latency_ms,
            "llm_first_token_ms": t.llm_first_token_ms,
            "tts_latency_ms": t.tts_latency_ms,
            "timestamp": t.timestamp.isoformat(),
        }
        for t in turns
    ]


@router.get("/metrics/summary")
async def metrics_summary() -> dict:
    collector = MetricsCollector()
    return await collector.snapshot()
