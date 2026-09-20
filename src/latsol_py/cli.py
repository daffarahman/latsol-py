"""Command-line interface for generating a quiz.

Usage::

    uv run latsol aljabar
    uv run python -m latsol_py himpunan --indent 0
"""

from __future__ import annotations

import argparse
import json
import sys

from .quiz import TOPICS, generate_quiz


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="latsol",
        description="Generate 5 soal UTBK-SNBT Pengetahuan Kuantitatif.",
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default=TOPICS[0],
        choices=list(TOPICS),
        help="Topic to generate questions for (default: %(default)s).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature (0.0-1.0).",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: %(default)s).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    quiz = generate_quiz(args.topic, temperature=args.temperature)
    json.dump(quiz, sys.stdout, ensure_ascii=False, indent=args.indent or None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
