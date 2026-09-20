"""Tests for the FastAPI layer (the LLM call is always stubbed)."""

from __future__ import annotations

from openai import APIConnectionError

import latsol_py.app as app_module
from latsol_py.config import Settings
from latsol_py.quiz import TOPICS, QuizGenerationError


def test_root(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "latsol-api"


def test_health(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_list_topics(client) -> None:
    response = client.get("/topics")
    assert response.status_code == 200
    assert response.json()["topics"] == list(TOPICS)


def test_get_quiz(client, monkeypatch, valid_quiz) -> None:
    monkeypatch.setattr(app_module, "generate_quiz", lambda topic, temperature=None: valid_quiz)
    response = client.get("/quiz", params={"topic": "aljabar"})
    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "aljabar"
    assert len(body["questions"]) == 5
    assert all(len(q["options"]) == 4 for q in body["questions"])


def test_post_quiz(client, monkeypatch, valid_quiz) -> None:
    monkeypatch.setattr(app_module, "generate_quiz", lambda topic, temperature=None: valid_quiz)
    response = client.post("/quiz", json={"topic": "peluang"})
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 5


def test_unknown_topic_is_rejected(client) -> None:
    assert client.get("/quiz", params={"topic": "fisika"}).status_code == 422
    assert client.post("/quiz", json={"topic": "fisika"}).status_code == 422


def test_generation_error_returns_502(client, monkeypatch) -> None:
    def boom(topic: str, temperature: float | None = None) -> dict:
        raise QuizGenerationError("model returned garbage")

    monkeypatch.setattr(app_module, "generate_quiz", boom)
    response = client.get("/quiz", params={"topic": "himpunan"})
    assert response.status_code == 502
    # Internal detail must not leak to the caller.
    assert "garbage" not in response.text


def test_upstream_connection_error_returns_503(client, monkeypatch) -> None:
    def boom(topic: str, temperature: float | None = None) -> dict:
        raise APIConnectionError(request=None)

    monkeypatch.setattr(app_module, "generate_quiz", boom)
    response = client.post("/quiz", json={"topic": "peluang"})
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_unexpected_error_returns_generic_500(client, monkeypatch) -> None:
    def boom(topic: str, temperature: float | None = None) -> dict:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(app_module, "generate_quiz", boom)
    response = client.get("/quiz", params={"topic": "aljabar"})
    assert response.status_code == 500
    assert "secret internal detail" not in response.text
    assert response.json() == {"detail": "Internal server error."}


def test_api_key_required_when_configured(client, monkeypatch, valid_quiz) -> None:
    monkeypatch.setattr(app_module, "settings", Settings(service_api_key="s3cret"))
    monkeypatch.setattr(app_module, "generate_quiz", lambda topic, temperature=None: valid_quiz)

    assert client.get("/quiz", params={"topic": "aljabar"}).status_code == 401
    wrong = client.get("/quiz", params={"topic": "aljabar"}, headers={"X-API-Key": "nope"})
    assert wrong.status_code == 401

    ok = client.get("/quiz", params={"topic": "aljabar"}, headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 200


def test_health_and_topics_stay_public_with_api_key(client, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "settings", Settings(service_api_key="s3cret"))
    assert client.get("/health").status_code == 200
    assert client.get("/topics").status_code == 200


def test_returns_503_when_at_capacity(client, monkeypatch) -> None:
    import threading

    monkeypatch.setattr(app_module, "_generation_slots", threading.BoundedSemaphore(0))
    response = client.get("/quiz", params={"topic": "aljabar"})
    assert response.status_code == 503
    assert response.headers.get("retry-after") == "5"
