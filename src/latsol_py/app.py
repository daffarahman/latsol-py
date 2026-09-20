"""FastAPI application exposing quiz generation over HTTP.

Run with::

    uv run uvicorn latsol_py.app:app --reload

Every successful request returns exactly 5 multiple-choice questions.

Security notes
--------------
* ``topic`` is an allowlist (``Literal`` of :data:`~latsol_py.quiz.TOPICS`), so no
  user-controlled text reaches the model prompt.
* Generation is capped by a process-wide semaphore to bound concurrency and cost.
* If ``LATSOL_SERVICE_API_KEY`` is set, mutating/expensive endpoints require an
  ``X-API-Key`` header.
* Upstream and validation failures are logged server-side and returned as generic
  messages so internal details are not leaked.
"""

from __future__ import annotations

import logging
import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from openai import APIConnectionError, APIError
from pydantic import BaseModel, Field

from .config import get_settings
from .quiz import TOPICS, QuizGenerationError, generate_quiz, validate_quiz

logger = logging.getLogger("latsol_py")

# Read once at import; tests may monkeypatch ``latsol_py.app.settings``.
settings = get_settings()

# Bound in-flight generations so a burst of requests cannot exhaust the worker
# threadpool or run up unbounded upstream cost.
_generation_slots = threading.BoundedSemaphore(max(1, settings.max_concurrency))

Topic = Literal[*TOPICS]  # type: ignore[valid-type]


class Option(BaseModel):
    content: str
    correct: bool


class Question(BaseModel):
    content: str
    options: list[Option]
    answerExplanation: str


class QuizResponse(BaseModel):
    topic: str
    questions: list[Question]


class QuizRequest(BaseModel):
    topic: Topic = Field(..., description="One of the supported topics.")
    temperature: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Optional sampling temperature."
    )


class TopicsResponse(BaseModel):
    topics: list[str]


def require_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """Enforce ``X-API-Key`` when ``LATSOL_SERVICE_API_KEY`` is configured.

    Auth is disabled (no-op) when no key is set, so local development is unchanged.
    """
    expected = settings.service_api_key
    if expected is None:
        return
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


@contextmanager
def _generation_slot() -> Iterator[None]:
    """Fail fast with 503 when the generator is at capacity."""
    if not _generation_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="The quiz generator is busy. Please retry shortly.",
            headers={"Retry-After": "5"},
        )
    try:
        yield
    finally:
        _generation_slots.release()


def _build_quiz(topic: str, temperature: float | None) -> QuizResponse:
    try:
        with _generation_slot():
            quiz = validate_quiz(generate_quiz(topic, temperature=temperature))
    except QuizGenerationError as exc:
        logger.warning("Invalid quiz generated for topic %r: %s", topic, exc)
        raise HTTPException(
            status_code=502,
            detail="The generator returned an invalid quiz. Please try again.",
        ) from exc
    except APIConnectionError as exc:  # includes APITimeoutError
        logger.error("Upstream LLM unreachable for topic %r: %s", topic, exc)
        raise HTTPException(
            status_code=503,
            detail="The quiz generator is temporarily unavailable. Please retry.",
        ) from exc
    except APIError as exc:
        logger.error("Upstream LLM error for topic %r: %s", topic, exc)
        raise HTTPException(
            status_code=502,
            detail="The quiz generator failed. Please try again.",
        ) from exc
    return QuizResponse(topic=topic, questions=quiz["questions"])


app = FastAPI(
    title="Latsol API",
    description=("Generate 5 Soal UTBK-SNBT Pengetahuan Kuantitatif (pilihan ganda) per request."),
    version="0.1.0",
    summary="Generator soal UTBK-SNBT Pengetahuan Kuantitatif.",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
    """Log unexpected errors and return a generic body (no internal details)."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/", summary="Service info")
def root() -> dict:
    info = {
        "service": "latsol-api",
        "topics": "/topics",
        "endpoints": ["GET /quiz?topic=...", "POST /quiz"],
    }
    if settings.docs_enabled:
        info["docs"] = "/docs"
    return info


@app.get("/health", summary="Health check")
def health() -> dict:
    return {"status": "ok"}


@app.get("/topics", response_model=TopicsResponse, summary="List supported topics")
def list_topics() -> TopicsResponse:
    return TopicsResponse(topics=list(TOPICS))


@app.get(
    "/quiz",
    response_model=QuizResponse,
    summary="Generate 5 soal (query params)",
    dependencies=[Depends(require_api_key)],
)
def get_quiz(
    topic: Annotated[Topic, Query(description="Topic to generate questions for.")],
    temperature: Annotated[
        float | None,
        Query(ge=0.0, le=1.0, description="Optional sampling temperature."),
    ] = None,
) -> QuizResponse:
    return _build_quiz(topic, temperature)


@app.post(
    "/quiz",
    response_model=QuizResponse,
    summary="Generate 5 soal (JSON body)",
    dependencies=[Depends(require_api_key)],
)
def post_quiz(request: QuizRequest) -> QuizResponse:
    return _build_quiz(request.topic, request.temperature)


def run() -> None:
    """Console-script entry point for ``latsol-api``."""
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("latsol_py.app:app", host="0.0.0.0", port=8000)
