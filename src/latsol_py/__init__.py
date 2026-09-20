"""latsol-py: generate UTBK-SNBT Pengetahuan Kuantitatif quizzes."""

from __future__ import annotations

from .config import Settings, get_settings
from .quiz import TOPICS, QuizGenerationError, generate_quiz, validate_quiz

__version__ = "0.1.0"

__all__ = [
    "TOPICS",
    "QuizGenerationError",
    "Settings",
    "generate_quiz",
    "get_settings",
    "validate_quiz",
    "__version__",
]
