"""Tests for environment-based configuration."""

from __future__ import annotations

import pytest

from latsol_py.config import Settings, get_settings


def test_defaults_are_used_when_env_is_unset(monkeypatch) -> None:
    for name in (
        "LATSOL_MODEL",
        "LATSOL_BASE_URL",
        "LATSOL_API_KEY",
        "LATSOL_TEMPERATURE",
        "LATSOL_MAX_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    assert get_settings() == Settings()
    get_settings.cache_clear()


def test_environment_overrides_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LATSOL_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("LATSOL_TEMPERATURE", "0.9")
    monkeypatch.setenv("LATSOL_MAX_TOKENS", "2048")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.model == "qwen2.5:7b"
    assert settings.temperature == 0.9
    assert settings.max_tokens == 2048
    get_settings.cache_clear()


def test_invalid_numeric_env_raises(monkeypatch) -> None:
    monkeypatch.setenv("LATSOL_TEMPERATURE", "hot")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="must be a number"):
        get_settings()
    get_settings.cache_clear()
