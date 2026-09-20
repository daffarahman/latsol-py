"""FastAPI application exposing quiz generation over HTTP.

Run with::

    uv run uvicorn latsol_py.app:app --reload

Every successful request returns exactly 5 multiple-choice questions.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .quiz import TOPICS, QuizGenerationError, generate_quiz, validate_quiz

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


def _build_quiz(topic: str, temperature: float | None) -> QuizResponse:
    try:
        quiz = generate_quiz(topic, temperature=temperature)
        quiz = validate_quiz(quiz)
    except QuizGenerationError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid quiz generated: {exc}") from exc
    return QuizResponse(topic=topic, questions=quiz["questions"])


app = FastAPI(
    title="Latsol API",
    description=("Generate 5 Soal UTBK-SNBT Pengetahuan Kuantitatif (pilihan ganda) per request."),
    version="0.1.0",
    summary="Generator soal UTBK-SNBT Pengetahuan Kuantitatif.",
)


@app.get("/", summary="Service info")
def root() -> dict:
    return {
        "service": "latsol-api",
        "docs": "/docs",
        "topics": "/topics",
        "endpoints": ["GET /quiz?topic=...", "POST /quiz"],
    }


@app.get("/health", summary="Health check")
def health() -> dict:
    return {"status": "ok"}


@app.get("/topics", response_model=TopicsResponse, summary="List supported topics")
def list_topics() -> TopicsResponse:
    return TopicsResponse(topics=list(TOPICS))


@app.get("/quiz", response_model=QuizResponse, summary="Generate 5 soal (query params)")
def get_quiz(
    topic: Annotated[Topic, Query(description="Topic to generate questions for.")],
    temperature: Annotated[
        float | None,
        Query(ge=0.0, le=1.0, description="Optional sampling temperature."),
    ] = None,
) -> QuizResponse:
    return _build_quiz(topic, temperature)


@app.post("/quiz", response_model=QuizResponse, summary="Generate 5 soal (JSON body)")
def post_quiz(request: QuizRequest) -> QuizResponse:
    return _build_quiz(request.topic, request.temperature)


def run() -> None:
    """Console-script entry point for ``latsol-api``."""
    import uvicorn

    uvicorn.run("latsol_py.app:app", host="0.0.0.0", port=8000)
