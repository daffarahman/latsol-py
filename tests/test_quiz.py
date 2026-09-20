"""Tests for the core quiz generation and validation logic."""

from __future__ import annotations

import pytest

from latsol_py.quiz import (
    TOPICS,
    QuizGenerationError,
    generate_quiz,
    load_system_prompt,
    validate_quiz,
)


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
