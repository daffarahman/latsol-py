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
        "LATSOL_REQUEST_TIMEOUT",
        "LATSOL_MAX_RETRIES",
        "LATSOL_MAX_CONCURRENCY",
        "LATSOL_SERVICE_API_KEY",
        "LATSOL_DOCS_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    assert get_settings() == Settings()
    get_settings.cache_clear()


def test_environment_overrides_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LATSOL_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("LATSOL_TEMPERATURE", "0.9")
    monkeypatch.setenv("LATSOL_MAX_TOKENS", "2048")
    monkeypatch.setenv("LATSOL_REQUEST_TIMEOUT", "12.5")
    monkeypatch.setenv("LATSOL_MAX_RETRIES", "0")
    monkeypatch.setenv("LATSOL_MAX_CONCURRENCY", "8")
    monkeypatch.setenv("LATSOL_SERVICE_API_KEY", "secret")
    monkeypatch.setenv("LATSOL_DOCS_ENABLED", "false")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.model == "qwen2.5:7b"
    assert settings.temperature == 0.9
    assert settings.max_tokens == 2048
    assert settings.request_timeout == 12.5
    assert settings.max_retries == 0
    assert settings.max_concurrency == 8
    assert settings.service_api_key == "secret"
    assert settings.docs_enabled is False
    get_settings.cache_clear()


def test_blank_service_api_key_disables_auth(monkeypatch) -> None:
    monkeypatch.setenv("LATSOL_SERVICE_API_KEY", "")
    get_settings.cache_clear()
    assert get_settings().service_api_key is None
    get_settings.cache_clear()


@pytest.mark.parametrize("raw", ["1", "true", "YES", "on"])
def test_truthy_docs_env(monkeypatch, raw: str) -> None:
    monkeypatch.setenv("LATSOL_DOCS_ENABLED", raw)
    get_settings.cache_clear()
    assert get_settings().docs_enabled is True
    get_settings.cache_clear()


def test_invalid_boolean_env_raises(monkeypatch) -> None:
    monkeypatch.setenv("LATSOL_DOCS_ENABLED", "maybe")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="must be a boolean"):
        get_settings()
    get_settings.cache_clear()


def test_invalid_numeric_env_raises(monkeypatch) -> None:
    monkeypatch.setenv("LATSOL_TEMPERATURE", "hot")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="must be a number"):
        get_settings()
    get_settings.cache_clear()
