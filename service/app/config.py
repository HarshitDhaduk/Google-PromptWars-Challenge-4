"""Application settings loaded from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor the .env lookup to the service directory so it works no matter
# where the process (or a reloader-spawned worker) was launched from.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Runtime configuration.

    Every field has a safe default so the service runs with zero configuration
    (demo mode). Setting GEMINI_API_KEY switches the assistant to live Gemini.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str | None = None
    # Rolling aliases keep fresh API keys working when Google retires pinned
    # model ids for new projects (as happened to gemini-2.5-flash). When the
    # primary model is capacity-crunched (503) the provider retries on the
    # fallback before degrading to demo mode.
    gemini_model: str = "gemini-flash-latest"
    gemini_fallback_model: str = "gemini-flash-lite-latest"

    # Deterministic crowd simulation seed; same seed => same crowd timeline.
    crowd_seed: int = 2026

    # Accelerated demo clock: sim starts at kickoff + offset and advances
    # `demo_speed` sim-minutes per real minute.
    demo_speed: float = 30.0
    demo_start_offset_min: float = -45.0

    # CORS allowlist for the Next.js app (defense in depth; the browser
    # normally reaches this service only through the Next.js BFF).
    web_origin: str = "http://localhost:3000"

    host: str = "127.0.0.1"
    port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
