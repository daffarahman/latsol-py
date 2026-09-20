"""Core quiz generation: prompt loading, schema, and validation.

This module is UI-agnostic so it can be reused by the FastAPI app, the CLI,
and tests.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from importlib.resources import files

from openai import OpenAI, OpenAIError

from .config import get_settings

logger = logging.getLogger("latsol_py")

# Appended to the conversation when the model's output fails validation, so the
# retry has concrete feedback rather than repeating the same mistake.
_CORRECTION_PROMPT = (
    "Respons sebelumnya tidak valid: {error} "
    "Kembalikan seluruh JSON untuk 5 soal sesuai skema. "
    'Pastikan setiap soal memiliki TEPAT SATU opsi dengan "correct": true '
    "dan tiga opsi lainnya false."
)

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


@lru_cache(maxsize=1)
def load_system_prompt() -> str:
    """Load the UTBK question-writer system prompt bundled with the package."""
    resource = files("latsol_py").joinpath("data", "system_prompt.txt")
    try:
        return resource.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:  # pragma: no cover - packaging error
        raise FileNotFoundError("Missing system prompt at data/system_prompt.txt") from exc


def check_upstream(timeout: float = 5.0) -> bool:
    """Return True if the configured model endpoint responds. Used by ``/ready``."""
    settings = get_settings()
    client = OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=timeout,
        max_retries=0,
    )
    try:
        client.models.list()
        return True
    except OpenAIError:
        return False


def validate_quiz(quiz: dict) -> dict:
    """Ensure exactly 5 questions, 4 options each, and one correct option each."""
    if not isinstance(quiz, dict):
        raise QuizGenerationError("Expected a JSON object with a 'questions' key.")

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


def generate_quiz(topic: str) -> dict:
    """Generate 5 multiple-choice questions for ``topic``.

    The model is asked up to ``LATSOL_MAX_ATTEMPTS`` times; if an attempt fails
    validation, the error is fed back and the model is asked to correct itself.

    Raises:
        ValueError: if ``topic`` is not one of :data:`TOPICS`.
        QuizGenerationError: if every attempt produces invalid output.
    """
    if topic not in TOPICS:
        raise ValueError(f"Unknown topic {topic!r}. Choose one of: {', '.join(TOPICS)}")

    settings = get_settings()
    client = OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": load_system_prompt()},
        {"role": "user", "content": f"Topik: {topic}"},
    ]
    attempts = max(1, settings.max_attempts)
    last_error: QuizGenerationError | None = None

    for attempt in range(1, attempts + 1):
        response = client.chat.completions.create(
            model=settings.model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "UTBKQuiz",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                },
            },
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )

        raw = response.choices[0].message.content
        if raw:
            try:
                return validate_quiz(json.loads(raw))
            except json.JSONDecodeError as exc:
                last_error = QuizGenerationError(f"The model returned invalid JSON: {exc}")
            except QuizGenerationError as exc:
                last_error = exc
        else:
            last_error = QuizGenerationError("The model returned an empty response.")

        logger.warning(
            "Attempt %d/%d for topic %r failed: %s", attempt, attempts, topic, last_error
        )
        if attempt < attempts:
            if raw:
                messages.append({"role": "assistant", "content": raw})
            messages.append(
                {"role": "user", "content": _CORRECTION_PROMPT.format(error=last_error)}
            )

    assert last_error is not None  # loop always sets it before exhausting
    raise last_error
