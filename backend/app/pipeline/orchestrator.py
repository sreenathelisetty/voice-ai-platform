"""
Pipeline orchestrator — owns the full lifecycle of one voice session.

Wires: WebSocket receiver → VAD → ASR → LLM → TTS → WebSocket sender
Each stage is an independent asyncio Task communicating via bounded queues.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import WebSocket

from app.db.repository import ensure_session, log_turn
from app.pipeline.asr import asr_worker
from app.pipeline.llm import llm_worker
from app.pipeline.tts import tts_worker
from app.pipeline.vad import VADProcessor
from app.session.manager import SessionManager
from app.session.models import PipelineResult
from app.utils.logging import get_logger

log = get_logger(__name__)

# Queue size caps provide back-pressure
ASR_QUEUE_SIZE = 5
LLM_QUEUE_SIZE = 5
TTS_QUEUE_SIZE = 10
WS_SEND_QUEUE_SIZE = 50


class PipelineOrchestrator:
    """
    One instance per active WebSocket session.
    Call `run()` to start all workers; they shut down gracefully when the
    WebSocket disconnects (detected by the receiver task).
    """

    def __init__(self, session_id: str, websocket: WebSocket, session_manager: SessionManager) -> None:
        self.session_id = session_id
        self._ws = websocket
        self._session_manager = session_manager

        # Inter-stage queues
        self._asr_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=ASR_QUEUE_SIZE)
        self._llm_queue: asyncio.Queue[tuple[str, PipelineResult] | None] = asyncio.Queue(maxsize=LLM_QUEUE_SIZE)
        self._tts_queue: asyncio.Queue[tuple[str, PipelineResult] | None] = asyncio.Queue(maxsize=TTS_QUEUE_SIZE)
        self._ws_send_queue: asyncio.Queue[bytes | str | None] = asyncio.Queue(maxsize=WS_SEND_QUEUE_SIZE)

        self._vad = VADProcessor(self._asr_queue)
        self._tasks: list[asyncio.Task[Any]] = []

    async def run(self) -> None:
        """Start all pipeline tasks and wait until the session ends."""
        # Spawn pipeline workers
        self._tasks = [
            asyncio.create_task(self._ws_receiver(), name=f"ws-recv-{self.session_id}"),
            asyncio.create_task(
                asr_worker(self._asr_queue, self._llm_queue, self.session_id, self._ws_send_queue),
                name=f"asr-{self.session_id}",
            ),
            asyncio.create_task(
                llm_worker(self._llm_queue, self._tts_queue, self.session_id, self._session_manager, self._ws_send_queue),
                name=f"llm-{self.session_id}",
            ),
            asyncio.create_task(
                tts_worker(self._tts_queue, self._ws_send_queue, self.session_id),
                name=f"tts-{self.session_id}",
            ),
            asyncio.create_task(self._ws_sender(), name=f"ws-send-{self.session_id}"),
        ]

        try:
            # Wait for all tasks; if any fail, cancel the rest
            await asyncio.gather(*self._tasks)
        except Exception as exc:
            log.error("pipeline_error", session_id=self.session_id, error=str(exc))
        finally:
            await self._shutdown()

    async def _ws_receiver(self) -> None:
        """Receive raw PCM binary frames from the WebSocket and feed VAD."""
        log.info("ws_receiver_started", session_id=self.session_id)
        try:
            while True:
                data = await self._ws.receive_bytes()
                self._vad.feed(data)
                await self._session_manager.touch(self.session_id)
        except Exception as exc:
            log.info("ws_receiver_ended", session_id=self.session_id, reason=str(exc))
        finally:
            self._vad.flush_remaining()
            await self._asr_queue.put(None)  # propagate shutdown sentinel

    async def _ws_sender(self) -> None:
        """Send audio frames and text events back to the client."""
        log.info("ws_sender_started", session_id=self.session_id)
        while True:
            frame = await self._ws_send_queue.get()
            if frame is None:
                break
            try:
                if isinstance(frame, str):
                    await self._ws.send_text(frame)
                else:
                    await self._ws.send_bytes(frame)
            except Exception as exc:
                log.warning("ws_send_failed", session_id=self.session_id, error=str(exc))
                break
        log.info("ws_sender_ended", session_id=self.session_id)

    async def _shutdown(self) -> None:
        for task in self._tasks:
            if not task.done():
                task.cancel()
        await self._session_manager.mark_disconnected(self.session_id)
        log.info("pipeline_shutdown", session_id=self.session_id)
