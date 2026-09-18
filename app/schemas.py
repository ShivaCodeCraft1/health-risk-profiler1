"""
Pydantic models for request/response bodies.

Design note: the assignment's expected outputs use exact field names
(answers, missing_fields, confidence, factors, risk_level, score,
rationale, recommendations, status). We mirror those names exactly so
API responses match the required JSON schemas.

Input is intentionally NOT a strict schema (no required fields) because
the assignment expects us to tolerate incomplete/noisy survey data and
report what's missing, rather than reject it outright.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.config import EXPECTED_FIELDS

# Re-exported here for backwards compatibility with any code/tests that
# import EXPECTED_FIELDS from app.schemas (its original home). The single
# source of truth is now app.config.
__all__ = ["EXPECTED_FIELDS"]


class TextParseRequest(BaseModel):
    """Body for POST /parse when the survey was typed, not scanned."""

    # Accepts any subset of EXPECTED_FIELDS (and possibly extra ones,
    # which we simply ignore downstream).
    # age: bounded to a plausible human age range (18-120) so obviously
    # invalid values (negative, or absurdly large) are rejected with a
    # controlled 422 instead of silently flowing into risk scoring.
    age: Optional[int] = Field(default=None, ge=18, le=120)
    smoker: Optional[bool] = None
    exercise: Optional[str] = None
    diet: Optional[str] = None


class ParseResponse(BaseModel):
    """Step 1 output — matches the assignment's 'Expected Output (JSON)'."""

    answers: dict[str, Any]
    missing_fields: list[str]
    confidence: float = Field(..., ge=0, le=1)


class IncompleteProfileResponse(BaseModel):
    """Guardrail output when >50% of expected fields are missing."""

    status: str = "incomplete_profile"
    reason: str = ">50% fields missing"


class FactorExtractionRequest(BaseModel):
    """Body for POST /extract-factors — takes Step 1's `answers` dict."""

    answers: dict[str, Any]


class FactorExtractionResponse(BaseModel):
    """Step 2 output — matches the assignment's 'Expected Output (JSON)'."""

    factors: list[str]
    confidence: float = Field(..., ge=0, le=1)


class RiskClassificationRequest(BaseModel):
    """Body for POST /classify-risk — Step 2's `factors` plus Step 1's `answers` (for age)."""

    factors: list[str]
    answers: dict[str, Any] = Field(default_factory=dict)


class RiskClassificationResponse(BaseModel):
    """Step 3 output — matches the assignment's 'Expected Output (JSON)'."""

    risk_level: str
    score: int = Field(..., ge=0, le=100)
    rationale: list[str]


class RecommendationRequest(BaseModel):
    """Body for POST /recommend — Step 3's `risk_level` plus Step 2's `factors`."""

    risk_level: str
    factors: list[str]


class RecommendationResponse(BaseModel):
    """Step 4 output — matches the assignment's 'Expected Output (JSON)'."""

    risk_level: str
    factors: list[str]
    recommendations: list[str]
    status: str = "ok"
