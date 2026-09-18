"""
Step 2 — Factor Extraction.

Converts normalized survey `answers` (Step 1 output) into a list of
human-readable risk `factors`, plus a `confidence` score.

This is deliberately simple, rule-based logic (no ML) — each answer is
checked against a threshold/condition and mapped to a plain-English
factor string, matching the assignment's Step 2 expected output:

    {"factors": ["smoking", "poor diet", "low exercise"], "confidence": 0.88}

Design notes (undocumented in the assignment, so documented here):
  - Each rule is independent — a field maps to a factor if its value
    matches a "risky" condition. Fields with no risky condition met
    contribute nothing (not an error, not a missing factor).
  - `confidence` reflects how much of the *available* answers could be
    turned into a factor decision. It intentionally does NOT reuse
    Step 1's confidence (that measured input quality; this measures
    how conclusively we could interpret the answers we did get).
"""

from typing import Any

from app.config import (
    FACTOR_CONFIDENCE_BASE,
    FACTOR_CONFIDENCE_RANGE,
    FACTOR_SCORABLE_FIELD_COUNT,
    LOW_EXERCISE_VALUES,
    POOR_DIET_KEYWORDS,
)


def extract_factors(answers: dict[str, Any]) -> tuple[list[str], float]:
    factors: list[str] = []
    evaluable = 0  # how many of the answers we could actually judge

    if "smoker" in answers:
        evaluable += 1
        if answers["smoker"] is True:
            factors.append("smoking")

    if "diet" in answers:
        evaluable += 1
        diet_value = str(answers["diet"]).lower()
        if any(keyword in diet_value for keyword in POOR_DIET_KEYWORDS):
            factors.append("poor diet")

    if "exercise" in answers:
        evaluable += 1
        exercise_value = str(answers["exercise"]).lower()
        if exercise_value in LOW_EXERCISE_VALUES:
            factors.append("low exercise")

    # `age` doesn't map to a standalone factor by itself in the
    # assignment's examples, so it's intentionally not scored here —
    # it's still available for use in risk classification (Step 3).

    confidence = (
        round(
            FACTOR_CONFIDENCE_BASE
            + FACTOR_CONFIDENCE_RANGE * (evaluable / FACTOR_SCORABLE_FIELD_COUNT),
            2,
        )
        if FACTOR_SCORABLE_FIELD_COUNT
        else 0.0
    )

    return factors, confidence
