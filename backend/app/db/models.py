"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    device_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    turns: Mapped[list[Turn]] = relationship("Turn", back_populates="session", cascade="all, delete-orphan")


class Turn(Base):
    """One full request-response cycle (user utterance + AI reply)."""

    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))            # "user" or "assistant"
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Latency breakdown (milliseconds)
    e2e_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asr_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_first_token_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_total_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    session: Mapped[Session] = relationship("Session", back_populates="turns")

    __table_args__ = (
        Index("ix_turns_session_timestamp", "session_id", "timestamp"),
    )


class MetricSnapshot(Base):
    """Hourly aggregated latency percentiles."""

    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    hour: Mapped[datetime] = mapped_column(DateTime, index=True)
    metric_name: Mapped[str] = mapped_column(String(64))
    p50_ms: Mapped[float] = mapped_column(Float)
    p95_ms: Mapped[float] = mapped_column(Float)
    p99_ms: Mapped[float] = mapped_column(Float)
    sample_count: Mapped[int] = mapped_column(Integer)
