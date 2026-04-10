"""
FastAPI application factory.
Lifespan: initialise all shared resources at startup, tear them down on shutdown.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.api.router import router
from app.api.websocket import ws_router
from app.config import get_settings
from app.pipeline.asr import load_whisper_model
from app.pipeline.tts import load_tts_model
from app.storage.postgres_client import check_db_health, close_db, get_engine
from app.storage.redis_client import close_redis, get_redis
from app.utils.logging import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    log.info("startup", env=settings.app_env)

    # Redis
    await get_redis()
    log.info("redis_ready")

    # PostgreSQL — create tables if they don't exist (dev convenience)
    if settings.app_env == "development":
        from app.db.models import Base
        from sqlalchemy.ext.asyncio import AsyncConnection
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("db_tables_created")

    # Pre-load heavy ML models to avoid cold-start latency on first request
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, load_whisper_model)
    log.info("whisper_ready")

    await loop.run_in_executor(None, load_tts_model)
    log.info("tts_ready")

    yield  # ── application runs ──────────────────────────────────────────────

    await close_redis()
    await close_db()
    log.info("shutdown_complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Voice AI Platform",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(router, prefix="/api/v1")
    app.include_router(ws_router)
    return app


app = create_app()
