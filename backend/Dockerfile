# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc g++ curl ffmpeg \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.cargo/bin:${PATH}"
RUN pip install --upgrade pip && \
    pip install --no-cache-dir build && \
    pip install --no-cache-dir \
        fastapi uvicorn[standard] websockets httpx \
        pydantic-settings python-dotenv \
        openai-whisper webrtcvad numpy \
        openai \
        TTS gTTS pydub \
        librosa soundfile opuslib \
        redis[hiredis] sqlalchemy[asyncio] asyncpg msgpack alembic \
        structlog tenacity

# ── Stage 2: model downloader ─────────────────────────────────────────────────
FROM builder AS model-downloader
WORKDIR /app
ENV XDG_DATA_HOME=/app/models/tts_cache
COPY scripts/download_whisper.py scripts/download_tts_model.py ./scripts/
RUN mkdir -p /app/models/whisper /app/models/tts /app/models/tts_cache && \
    python scripts/download_whisper.py && \
    python scripts/download_tts_model.py

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# System runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
        libopus0 ffmpeg \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Non-root user with home dir
RUN groupadd -r voice 2>/dev/null || true && \
    useradd -r -g voice -u 1000 -m -d /home/voice voice 2>/dev/null || true

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pre-downloaded models
COPY --from=model-downloader /app/models /app/models

# App source
WORKDIR /app
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .

# Set permissions
RUN chown -R voice:voice /app /home/voice
USER voice

ENV NUMBA_CACHE_DIR=/tmp/numba_cache
ENV XDG_DATA_HOME=/app/models/tts_cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
