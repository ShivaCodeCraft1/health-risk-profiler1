"""
Step 4 — Recommendations.

Converts the detected `factors` into actionable, non-diagnostic
lifestyle recommendations, matching the assignment's Step 4 expected
output:

    {
      "risk_level": "high",
      "factors": ["smoking", "poor diet", "low exercise"],
      "recommendations": ["Quit smoking", "Reduce sugar", "Walk 30 mins daily"],
      "status": "ok"
    }

Design notes (undocumented in the assignment, so documented here):
  - One fixed recommendation per known factor (simple lookup table,
    same rule-based pattern as factor extraction and risk scoring —
    no ML, fully explainable).
  - Recommendations are always phrased as general, non-diagnostic
    lifestyle guidance ("Reduce sugar"), never medical instructions
    ("Take medication X") or a diagnosis.
  - If a factor isn't in the lookup table, it's silently skipped
    rather than raising an error — keeps the pipeline resilient to
    factors added later without a matching recommendation yet.
"""

from app.config import FACTOR_RECOMMENDATIONS


def generate_recommendations(factors: list[str]) -> list[str]:
    recommendations = []
    for factor in factors:
        recommendation = FACTOR_RECOMMENDATIONS.get(factor)
        if recommendation:
            recommendations.append(recommendation)
    return recommendations
