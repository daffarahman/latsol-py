"""Tests for the FastAPI layer (the LLM call is always stubbed)."""

from __future__ import annotations

import latsol_py.app as app_module
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
