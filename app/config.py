"""
Centralized configuration and constants.

This file exists purely to consolidate values that were previously
scattered across schemas.py, ocr_parser.py, factor_extraction.py,
risk_classifier.py, recommendations.py, and pipeline.py. No values
were changed during this move — every number/mapping here is
byte-for-byte identical to what existed before.

Everything in this project is a fixed, rule-based lookup or formula —
there is no trained model and no external configuration file. Values
are grouped by which pipeline step they belong to.
"""

# ---------------------------------------------------------------------------
# Step 1 — OCR / Text Parsing
# ---------------------------------------------------------------------------

# The set of survey fields we know how to look for.
# Based only on the fields shown in the assignment's sample input/output.
# Extend this list if your actual survey form has more fields.
EXPECTED_FIELDS = ["age", "smoker", "exercise", "diet"]

# Normalizes common yes/no phrasings picked up from typed or OCR'd text.
TRUTHY_VALUES = {"yes", "y", "true", "1"}
FALSY_VALUES = {"no", "n", "false", "0"}

# Confidence heuristic constants (not a statistical measure — see README
# "Design notes" for why these specific numbers were chosen).
TEXT_BASE_CONFIDENCE = 0.97
TEXT_CONFIDENCE_PENALTY_PER_MISSING = 0.05

OCR_BASE_CONFIDENCE = 0.90  # OCR is noisier than typed input
OCR_CONFIDENCE_PENALTY_PER_MISSING = 0.08

# ---------------------------------------------------------------------------
# Guardrail (shared by both text and image input paths)
# ---------------------------------------------------------------------------

MISSING_FIELD_THRESHOLD = 0.5  # >50% missing triggers the guardrail

# ---------------------------------------------------------------------------
# Step 2 — Factor Extraction
# ---------------------------------------------------------------------------

LOW_EXERCISE_VALUES = {"rarely", "never", "none", "no"}
POOR_DIET_KEYWORDS = {"high sugar", "high fat", "junk", "processed", "fast food"}

# Number of answer fields that factor extraction can actually judge
# (smoker, diet, exercise — age is used later, in risk classification).
FACTOR_SCORABLE_FIELD_COUNT = 3
FACTOR_CONFIDENCE_BASE = 0.6
FACTOR_CONFIDENCE_RANGE = 0.4

# ---------------------------------------------------------------------------
# Step 3 — Risk Classification
# ---------------------------------------------------------------------------

# Fixed point-based scoring. This is a simple, fully explainable,
# NON-DIAGNOSTIC, rule-based educational scoring system — not a
# medically validated model of any kind.
FACTOR_POINTS = {
    "smoking": 35,
    "poor diet": 25,
    "low exercise": 20,
}

AGE_60_PLUS_POINTS = 15
AGE_40_PLUS_POINTS = 8
AGE_60_THRESHOLD = 60
AGE_40_THRESHOLD = 40

MAX_SCORE = 100
RISK_LOW_MAX = 29     # score 0-29   -> "low"
RISK_MEDIUM_MAX = 59  # score 30-59  -> "medium"; 60-100 -> "high"

# ---------------------------------------------------------------------------
# Step 4 — Recommendations
# ---------------------------------------------------------------------------

FACTOR_RECOMMENDATIONS = {
    "smoking": "Quit smoking",
    "poor diet": "Reduce sugar",
    "low exercise": "Walk 30 mins daily",
}
