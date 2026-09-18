"""
Step 3 — Risk Classification.

Converts Step 2's `factors` (plus the original `answers`, for age) into
a simple, explainable, non-diagnostic risk score.

This is deliberately a fixed point-based formula (no ML, no trained
weights) so every score is fully explainable via `rationale` — matching
the assignment's "simple scoring logic (non-diagnostic)" requirement.

Design notes (undocumented in the assignment, so documented here):
  - Each factor contributes a fixed number of points.
  - Age adds a small additional risk contribution past age 40/60,
    reflecting general population risk trends — NOT a medical judgment
    about any individual.
  - Score is capped at 100.
  - Buckets: 0-29 = low, 30-59 = medium, 60-100 = high.
  - `rationale` lists the plain-language reasons behind the score,
    reusing the same factor strings from Step 2 plus an age note when
    relevant (rather than inventing new wording per factor).
"""

from typing import Any

from app.config import (
    AGE_40_PLUS_POINTS,
    AGE_40_THRESHOLD,
    AGE_60_PLUS_POINTS,
    AGE_60_THRESHOLD,
    FACTOR_POINTS,
    MAX_SCORE,
    RISK_LOW_MAX,
    RISK_MEDIUM_MAX,
)


def _age_points(age: Any) -> tuple[int, str | None]:
    if not isinstance(age, int):
        return 0, None
    if age >= AGE_60_THRESHOLD:
        return AGE_60_PLUS_POINTS, "age 60+"
    if age >= AGE_40_THRESHOLD:
        return AGE_40_PLUS_POINTS, "age 40+"
    return 0, None


def _bucket(score: int) -> str:
    if score <= RISK_LOW_MAX:
        return "low"
    if score <= RISK_MEDIUM_MAX:
        return "medium"
    return "high"


def classify_risk(factors: list[str], answers: dict[str, Any]) -> tuple[str, int, list[str]]:
    score = 0
    rationale: list[str] = []

    for factor in factors:
        points = FACTOR_POINTS.get(factor, 0)
        if points:
            score += points
            rationale.append(factor)

    age_points, age_note = _age_points(answers.get("age"))
    if age_points:
        score += age_points
        rationale.append(age_note)

    score = min(score, MAX_SCORE)
    risk_level = _bucket(score)

    return risk_level, score, rationale
