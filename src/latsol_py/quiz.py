"""Core quiz generation: prompt loading, schema, and validation.

This module is UI-agnostic so it can be reused by the FastAPI app, the CLI,
and tests.
"""

from __future__ import annotations

import json
from importlib.resources import files

from openai import OpenAI

from .config import get_settings

# --- Topics the service can generate ---
TOPICS: tuple[str, ...] = (
    "aljabar",
    "himpunan",
    "persamaan garis (fungsi linear dan kuadrat)",
    "trigonometri",
    "fungsi invers",
    "statistika data tunggal",
    "barisan dan deret",
    "peluang",
)

PROMPT_RESOURCE = ("data", "system_prompt.txt")

# --- JSON Schema the model must obey ---
RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 5,
            "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "correct": {"type": "boolean"},
                            },
                            "required": ["content", "correct"],
                            "additionalProperties": False,
                        },
                    },
                    "answerExplanation": {"type": "string"},
                },
                "required": ["content", "options", "answerExplanation"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}


class QuizGenerationError(RuntimeError):
    """Raised when the model output is missing, malformed, or invalid."""


def load_system_prompt() -> str:
    """Load the UTBK question-writer system prompt bundled with the package."""
    resource = files("latsol_py").joinpath(*PROMPT_RESOURCE)
    try:
        return resource.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:  # pragma: no cover - packaging error
        raise FileNotFoundError(f"Missing system prompt at {'.'.join(PROMPT_RESOURCE)}") from exc


def validate_quiz(quiz: dict) -> dict:
    """Ensure exactly 5 questions, 4 options each, and one correct option each."""
    questions = quiz.get("questions")
    if not isinstance(questions, list) or len(questions) != 5:
        raise QuizGenerationError("Expected exactly 5 questions.")

    for index, question in enumerate(questions, start=1):
        options = question.get("options")
        if not isinstance(options, list) or len(options) != 4:
            raise QuizGenerationError(f"Question {index} must have exactly 4 options.")
        if sum(1 for option in options if option.get("correct") is True) != 1:
            raise QuizGenerationError(f"Question {index} must have exactly one correct option.")
        if not question.get("content") or not question.get("answerExplanation"):
            raise QuizGenerationError(f"Question {index} is missing content or answerExplanation.")
    return quiz


def generate_quiz(topic: str, temperature: float | None = None) -> dict:
    """Generate 5 multiple-choice questions for ``topic``.

    Raises:
        ValueError: if ``topic`` is not one of :data:`TOPICS`.
        QuizGenerationError: if the model output is invalid.
    """
    if topic not in TOPICS:
        raise ValueError(f"Unknown topic {topic!r}. Choose one of: {', '.join(TOPICS)}")

    settings = get_settings()
    client = OpenAI(base_url=settings.base_url, api_key=settings.api_key)

    response = client.chat.completions.create(
        model=settings.model,
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": f"Topik: {topic}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "UTBKQuiz",
                "strict": True,
                "schema": RESPONSE_SCHEMA,
            },
        },
        temperature=settings.temperature if temperature is None else temperature,
        max_tokens=settings.max_tokens,
    )

    raw = response.choices[0].message.content
    if not raw:
        raise QuizGenerationError("The model returned an empty response.")
    try:
        quiz = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QuizGenerationError(f"The model returned invalid JSON: {exc}") from exc

    return validate_quiz(quiz)
