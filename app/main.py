from typing import Union

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

from app.factor_extraction import extract_factors
from app.ocr_parser import OCRProcessingError, parse_image, parse_text
from app.pipeline import incomplete_profile_response, is_incomplete_profile, run_full_pipeline
from app.recommendations import generate_recommendations
from app.risk_classifier import classify_risk
from app.schemas import (
    FactorExtractionRequest,
    FactorExtractionResponse,
    IncompleteProfileResponse,
    ParseResponse,
    RecommendationRequest,
    RecommendationResponse,
    RiskClassificationRequest,
    RiskClassificationResponse,
    TextParseRequest,
)

app = FastAPI(
    title="Health Risk Profiler",
    description=(
        "Educational, non-diagnostic health risk profiling API. "
        "Parses lifestyle survey answers (typed or scanned), extracts "
        "risk factors, computes a simple rule-based risk score, and "
        "returns actionable, non-diagnostic recommendations. This is "
        "NOT a medical device and makes no clinical claims."
    ),
    version="0.1.0",
)


@app.get("/")
async def root():
    """Basic API info — not part of the assignment's required schemas,
    just a friendly landing response so hitting the base URL doesn't 404."""
    return {
        "name": "Health Risk Profiler",
        "version": app.version,
        "docs": "/docs",
        "health_check": "/health",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/parse")
async def parse_text_endpoint(payload: TextParseRequest):
    """Step 1 — parse a typed/JSON survey submission."""
    answers, missing, confidence = parse_text(payload.model_dump())

    if is_incomplete_profile(missing):
        return JSONResponse(content=incomplete_profile_response())

    result = ParseResponse(answers=answers, missing_fields=missing, confidence=confidence)
    return result


@app.post("/extract-factors", response_model=FactorExtractionResponse)
async def extract_factors_endpoint(payload: FactorExtractionRequest):
    """Step 2 — turn Step 1's `answers` into human-readable risk factors."""
    factors, confidence = extract_factors(payload.answers)
    return FactorExtractionResponse(factors=factors, confidence=confidence)


@app.post("/classify-risk", response_model=RiskClassificationResponse)
async def classify_risk_endpoint(payload: RiskClassificationRequest):
    """Step 3 — turn Step 2's `factors` (+ answers, for age) into a risk score."""
    risk_level, score, rationale = classify_risk(payload.factors, payload.answers)
    return RiskClassificationResponse(risk_level=risk_level, score=score, rationale=rationale)


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_endpoint(payload: RecommendationRequest):
    """Step 4 — turn Step 3's `risk_level` + Step 2's `factors` into recommendations."""
    recommendations = generate_recommendations(payload.factors)
    return RecommendationResponse(
        risk_level=payload.risk_level,
        factors=payload.factors,
        recommendations=recommendations,
    )


@app.post("/parse-image")
async def parse_image_endpoint(file: UploadFile = File(...)):
    """Step 1 — parse a scanned/photographed survey form via OCR."""
    image_bytes = await file.read()
    try:
        answers, missing, confidence = parse_image(image_bytes)
    except OCRProcessingError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(exc)})

    if is_incomplete_profile(missing):
        return JSONResponse(content=incomplete_profile_response())

    result = ParseResponse(answers=answers, missing_fields=missing, confidence=confidence)
    return result


@app.post("/profile", response_model=Union[RecommendationResponse, IncompleteProfileResponse])
async def profile_from_text(payload: TextParseRequest):
    """
    Full pipeline (Steps 1-4) for typed/JSON input, in one call.

    Chains: parse_text -> guardrail check -> extract_factors ->
    classify_risk -> generate_recommendations.
    """
    answers, missing, _confidence = parse_text(payload.model_dump())
    result = run_full_pipeline(answers, missing)
    return JSONResponse(content=result)


@app.post("/profile-image", response_model=Union[RecommendationResponse, IncompleteProfileResponse])
async def profile_from_image(file: UploadFile = File(...)):
    """
    Full pipeline (Steps 1-4) for a scanned/photographed form, in one call.

    Chains: parse_image (OCR) -> guardrail check -> extract_factors ->
    classify_risk -> generate_recommendations.
    """
    image_bytes = await file.read()
    try:
        answers, missing, _confidence = parse_image(image_bytes)
    except OCRProcessingError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(exc)})

    result = run_full_pipeline(answers, missing)
    return JSONResponse(content=result)
