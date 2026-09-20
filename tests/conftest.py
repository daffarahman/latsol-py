"""Shared pytest fixtures and helpers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from latsol_py.app import app


def make_question(correct_index: int = 0) -> dict:
    """Build one well-formed question with the correct option at ``correct_index``."""
    return {
        "content": "Berapakah nilai \\(x\\)?",
        "options": [{"content": f"Opsi {i}", "correct": i == correct_index} for i in range(4)],
        "answerExplanation": "Karena \\(x = 1\\).",
    }


@pytest.fixture
def valid_quiz() -> dict:
    return {"questions": [make_question(i % 4) for i in range(5)]}


@pytest.fixture
def client() -> TestClient:
    # raise_server_exceptions=False so the generic 500 handler is exercised
    # instead of the exception propagating into the test.
    return TestClient(app, raise_server_exceptions=False)
