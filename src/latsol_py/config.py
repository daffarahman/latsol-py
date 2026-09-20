"""Runtime configuration, loaded from environment variables.

All values have sensible defaults for a local Ollama setup, so the service
works out of the box while remaining configurable in deployment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Load a local `.env` (if present) into the environment before any settings are
# read. Existing environment variables always win, so deployments can override
# file-based defaults.
load_dotenv()


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings."""

    model: str = "llama3.1:8b"
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    temperature: float = 0.4
    max_tokens: int = 4096


# A default instance is used as the source of fallback values. With ``slots=True``
# the class attributes are slot descriptors, not the default values, so we cannot
# read them off the class itself.
_DEFAULTS = Settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, read once from the environment."""
    return Settings(
        model=os.getenv("LATSOL_MODEL", _DEFAULTS.model),
        base_url=os.getenv("LATSOL_BASE_URL", _DEFAULTS.base_url),
        api_key=os.getenv("LATSOL_API_KEY", _DEFAULTS.api_key),
        temperature=_env_float("LATSOL_TEMPERATURE", _DEFAULTS.temperature),
        max_tokens=_env_int("LATSOL_MAX_TOKENS", _DEFAULTS.max_tokens),
    )
