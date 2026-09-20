"""Tests for the core quiz generation and validation logic."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

import latsol_py.quiz as quiz_module
from latsol_py.quiz import (
    TOPICS,
    QuizGenerationError,
    generate_quiz,
    load_system_prompt,
    validate_quiz,
)


class FakeClient:
    """Minimal stand-in for ``openai.OpenAI`` that replays canned responses."""

    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)
        self.calls = 0
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls += 1
        content = self._outputs.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_topics_are_defined() -> None:
    assert len(TOPICS) == 8
    assert "aljabar" in TOPICS


def test_system_prompt_is_loaded() -> None:
    prompt = load_system_prompt()
    assert "UTBK" in prompt
    assert len(prompt) > 100


def test_validate_accepts_well_formed_quiz(valid_quiz: dict) -> None:
    assert validate_quiz(valid_quiz) is valid_quiz


def test_validate_rejects_wrong_question_count(valid_quiz: dict) -> None:
    valid_quiz["questions"] = valid_quiz["questions"][:4]
    with pytest.raises(QuizGenerationError, match="exactly 5 questions"):
        validate_quiz(valid_quiz)


def test_validate_rejects_wrong_option_count(valid_quiz: dict) -> None:
    valid_quiz["questions"][0]["options"] = valid_quiz["questions"][0]["options"][:3]
    with pytest.raises(QuizGenerationError, match="4 options"):
        validate_quiz(valid_quiz)


def test_validate_rejects_multiple_correct_options(valid_quiz: dict) -> None:
    valid_quiz["questions"][0]["options"][1]["correct"] = True
    with pytest.raises(QuizGenerationError, match="one correct option"):
        validate_quiz(valid_quiz)


def test_validate_rejects_missing_explanation(valid_quiz: dict) -> None:
    valid_quiz["questions"][2]["answerExplanation"] = ""
    with pytest.raises(QuizGenerationError, match="answerExplanation"):
        validate_quiz(valid_quiz)


def test_generate_quiz_rejects_unknown_topic() -> None:
    with pytest.raises(ValueError, match="Unknown topic"):
        generate_quiz("fisika")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Keep each test's environment from leaking into the cached settings."""
    quiz_module.get_settings.cache_clear()
    yield
    quiz_module.get_settings.cache_clear()


def _wrong_correct_count_json(valid_quiz: dict) -> str:
    """A response where question 1 has zero correct options."""
    broken = copy.deepcopy(valid_quiz)
    for option in broken["questions"][0]["options"]:
        option["correct"] = False
    return json.dumps(broken)


def _patch_client(monkeypatch, outputs: list[str]) -> FakeClient:
    client = FakeClient(outputs)
    monkeypatch.setattr(quiz_module, "OpenAI", lambda **kwargs: client)
    return client


def test_generate_retries_when_first_output_is_invalid(monkeypatch, valid_quiz) -> None:
    monkeypatch.setenv("LATSOL_MAX_ATTEMPTS", "2")
    client = _patch_client(
        monkeypatch, [_wrong_correct_count_json(valid_quiz), json.dumps(valid_quiz)]
    )

    result = quiz_module.generate_quiz("aljabar")

    assert client.calls == 2
    assert len(result["questions"]) == 5


def test_generate_raises_after_exhausting_attempts(monkeypatch, valid_quiz) -> None:
    monkeypatch.setenv("LATSOL_MAX_ATTEMPTS", "2")
    client = _patch_client(monkeypatch, [_wrong_correct_count_json(valid_quiz)] * 3)

    with pytest.raises(QuizGenerationError, match="one correct option"):
        quiz_module.generate_quiz("aljabar")

    assert client.calls == 2
