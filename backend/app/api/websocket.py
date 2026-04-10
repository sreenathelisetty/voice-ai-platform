"""
WebSocket endpoint — /ws/{session_id}

Authenticates via ?token= query param.
Spawns a PipelineOrchestrator per connection.
Handles reconnection via Redis reconnect window.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.db.repository import ensure_session
from app.pipeline.orchestrator import PipelineOrchestrator
from app.session.manager import SessionManager
from app.utils.exceptions import AuthenticationError
from app.utils.logging import get_logger

log = get_logger(__name__)
ws_router = APIRouter()
session_manager = SessionManager()


@ws_router.websocket("/ws/{session_id}")
async def voice_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(default=""),
    user_id: str | None = Query(default=None),
    device_type: str | None = Query(default=None),
) -> None:
    settings = get_settings()

    # Authentication
    if token != settings.api_token:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    log.info("ws_connected", session_id=session_id, user_id=user_id, device_type=device_type)

    try:
        # Determine if this is a fresh session or a reconnect
        can_reconnect = await session_manager.can_reconnect(session_id)
        if can_reconnect:
            log.info("session_reconnected", session_id=session_id)
            state = await session_manager.get(session_id)
        else:
            state = await session_manager.create(
                session_id=session_id,
                user_id=user_id,
                device_type=device_type,
            )
            await ensure_session(session_id=session_id, user_id=user_id, device_type=device_type)

        # Send session confirmation to client
        await websocket.send_text(json.dumps({
            "type": "session_ready",
            "session_id": session_id,
            "reconnected": can_reconnect,
        }))

        # Run the full pipeline — blocks until disconnection
        orchestrator = PipelineOrchestrator(session_id, websocket, session_manager)
        await orchestrator.run()

    except WebSocketDisconnect as exc:
        log.info("ws_disconnected", session_id=session_id, code=exc.code)
    except Exception as exc:
        log.error("ws_error", session_id=session_id, error=str(exc))
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        await session_manager.mark_disconnected(session_id)
        log.info("ws_closed", session_id=session_id)
