"""
Centralised configuration via pydantic-settings.
All values read from environment variables / .env file.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── OpenAI / NVIDIA ───────────────────────────────────────────────────────
    openai_api_key: str = ""
    openai_base_url: str = "https://integrate.api.nvidia.com/v1"
    openai_model: str = "openai/gpt-oss-20b"
    openai_max_tokens: int = 1024
    openai_temperature: float = 0.7
    nvidia_api_key: str = ""

    # ── Whisper ───────────────────────────────────────────────────────────────
    whisper_model_size: str = "small.en"
    whisper_device: str = "cpu"
    whisper_model_dir: str = "/app/models/whisper"

    # ── TTS ───────────────────────────────────────────────────────────────────
    tts_model_name: str = "tts_models/en/ljspeech/fast_pitch"
    tts_model_dir: str = "/app/models/tts"
    tts_sample_rate: int = 22050
    tts_output_sample_rate: int = 24000

    # ── Audio ─────────────────────────────────────────────────────────────────
    audio_input_sample_rate: int = 16000
    audio_chunk_duration_ms: int = 100
    vad_aggressiveness: int = 2
    vad_silence_threshold_ms: int = 800
    opus_bitrate: int = 64000

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl_seconds: int = 1800
    redis_reconnect_window_seconds: int = 60
    redis_max_history_turns: int = 20

    # ── PostgreSQL ────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://voice:voice@localhost:5432/voiceai"
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "change-me"
    api_token: str = "dev-token"

    # ── AWS ───────────────────────────────────────────────────────────────────
    aws_region: str = "us-east-1"
    aws_cloudwatch_log_group: str = "/voice-ai/backend"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def vad_silence_frames(self) -> int:
        """Number of 20ms VAD frames that constitute end-of-utterance."""
        return self.vad_silence_threshold_ms // 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
