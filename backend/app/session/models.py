"""Pydantic models for session state and pipeline data."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"


class ConversationTurn(BaseModel):
    role: str                        # "user" or "assistant"
    content: str
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())


class SessionState(BaseModel):
    session_id: str
    user_id: str | None = None
    device_type: str | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    last_active: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    history: list[ConversationTurn] = Field(default_factory=list)


class PipelineResult(BaseModel):
    """Timing data collected as a turn flows through the pipeline."""
    session_id: str
    transcript: str | None = None
    response_text: str | None = None
    asr_start: float | None = None
    asr_end: float | None = None
    llm_first_token: float | None = None
    llm_end: float | None = None
    tts_start: float | None = None
    tts_end: float | None = None
    turn_start: float | None = None

    @property
    def asr_latency_ms(self) -> int | None:
        if self.asr_start and self.asr_end:
            return int((self.asr_end - self.asr_start) * 1000)
        return None

    @property
    def llm_first_token_ms(self) -> int | None:
        if self.asr_end and self.llm_first_token:
            return int((self.llm_first_token - self.asr_end) * 1000)
        return None

    @property
    def llm_total_ms(self) -> int | None:
        if self.asr_end and self.llm_end:
            return int((self.llm_end - self.asr_end) * 1000)
        return None

    @property
    def tts_latency_ms(self) -> int | None:
        if self.tts_start and self.tts_end:
            return int((self.tts_end - self.tts_start) * 1000)
        return None

    @property
    def e2e_latency_ms(self) -> int | None:
        if self.turn_start and self.tts_end:
            return int((self.tts_end - self.turn_start) * 1000)
        return None
