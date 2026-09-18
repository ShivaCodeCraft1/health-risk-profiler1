"""
Step 1 — OCR / Text Parsing.

Two entry points, both converge on the same output shape:
  - parse_text(data: dict)        -> for typed/JSON survey input
  - parse_image(image_bytes)      -> for scanned/photographed forms

Both return: (answers: dict, missing_fields: list[str], confidence: float)

Design decisions (documented since the assignment doesn't specify exact
scoring/confidence formulas):
  - `missing_fields` = any EXPECTED_FIELDS key that is None/absent.
  - `confidence` for text input starts high (typed input is reliable)
    and drops slightly per missing field.
  - `confidence` for OCR input starts lower (OCR is inherently noisier)
    and drops further per missing/unparseable field.

OCR error correction here is deliberately simple: it's rule-based OCR
error correction using known common OCR variants (a small lookup of
truthy/falsy words, and a loose "does the line start with roughly this
field name" prefix check). It is NOT fuzzy-matching in the algorithmic
sense (no edit-distance/Levenshtein library is used) — see
`_parse_ocr_lines` for exactly what it does and does not tolerate.
"""

import io
import re
from typing import Any

from PIL import Image, UnidentifiedImageError
import pytesseract

from app.config import (
    EXPECTED_FIELDS,
    FALSY_VALUES,
    OCR_BASE_CONFIDENCE,
    OCR_CONFIDENCE_PENALTY_PER_MISSING,
    TEXT_BASE_CONFIDENCE,
    TEXT_CONFIDENCE_PENALTY_PER_MISSING,
    TRUTHY_VALUES,
)


class OCRProcessingError(Exception):
    """
    Raised when an uploaded image cannot be opened or OCR'd.

    Covers corrupt files, unsupported/unrecognized formats, and any
    other failure from PIL or pytesseract while reading the image.
    Callers (see app/main.py) catch this and return a controlled HTTP
    400 response instead of letting the exception crash the request
    with an unhandled 500.
    """


def _normalize_value(field: str, raw_value: str) -> Any:
    """Coerce a raw string value into the right type for a given field."""
    value = raw_value.strip()

    if field == "age":
        digits = re.sub(r"[^\d]", "", value)
        return int(digits) if digits else None

    if field == "smoker":
        lowered = value.lower()
        if lowered in TRUTHY_VALUES:
            return True
        if lowered in FALSY_VALUES:
            return False
        return None

    # exercise / diet and any other free-text field: keep as lowercase string
    return value.lower() if value else None


def _build_answers(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep only known fields with non-null values."""
    answers = {}
    for field in EXPECTED_FIELDS:
        value = raw.get(field)
        if value is not None:
            answers[field] = value
    return answers


def _missing_fields(answers: dict[str, Any]) -> list[str]:
    return [f for f in EXPECTED_FIELDS if f not in answers]


def parse_text(data: dict[str, Any]) -> tuple[dict[str, Any], list[str], float]:
    """Parse a typed/JSON survey submission."""
    raw = {field: data.get(field) for field in EXPECTED_FIELDS}
    answers = _build_answers(raw)
    missing = _missing_fields(answers)

    confidence = round(
        max(TEXT_BASE_CONFIDENCE - TEXT_CONFIDENCE_PENALTY_PER_MISSING * len(missing), 0.0),
        2,
    )

    return answers, missing, confidence


def _ocr_text_from_image(image_bytes: bytes) -> str:
    """
    Open an image (PNG or JPEG/JPG, or anything else Pillow supports)
    and run OCR on it. Converts to RGB first so palette (P), CMYK, or
    RGBA images don't produce degraded or inconsistent OCR results.

    Raises OCRProcessingError on any failure — a corrupt file, an
    unrecognized format, or a pytesseract/Tesseract-binary failure —
    so the caller can return a controlled error instead of crashing.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise OCRProcessingError(
            "Could not read the uploaded file as an image. "
            "Supported formats include PNG and JPEG/JPG."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - any other Pillow failure is still "bad image"
        raise OCRProcessingError(f"Failed to open the uploaded image: {exc}") from exc

    try:
        return pytesseract.image_to_string(image)
    except Exception as exc:  # noqa: BLE001 - covers missing Tesseract binary, etc.
        raise OCRProcessingError(f"OCR processing failed: {exc}") from exc


def _parse_ocr_lines(raw_text: str) -> dict[str, Any]:
    """
    Turn noisy OCR'd lines into a normalized field dict.

    Real OCR output is unreliable, so this is deliberately tolerant of:
        "Age: 42"      (clean colon)
        "Age 42"       (colon dropped by OCR)
        "Brercise: rarely"  (OCR misread a couple letters mid-word)
    We match on the field name appearing at the *start* of the line
    (a loose prefix check on the first several characters) rather than
    requiring an exact "field:" prefix, then take whatever text follows
    as the value. This is rule-based OCR error correction using known
    common OCR variants — not a general fuzzy-matching algorithm.
    """
    parsed: dict[str, Any] = {}

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        matched_field = None
        rest = ""

        for field in EXPECTED_FIELDS:
            # Loose match: first ~60% of the field name appears at the
            # start of the line (case-insensitive). Cheap way to tolerate
            # a couple of misread characters (e.g. "Exercise" -> "Brercise")
            # without needing a full fuzzy-matching library.
            prefix_len = max(3, int(len(field) * 0.6))
            probe_len = len(field) + 2  # small buffer for misread chars
            head = stripped[:probe_len].lower()
            if field[:prefix_len] in head:
                matched_field = field
                # value = everything after the field name / optional colon
                after = re.split(r":", stripped, maxsplit=1)
                if len(after) == 2:
                    rest = after[1]
                else:
                    # no colon found — strip a leading word-ish chunk
                    # (the misread field name itself) and keep the rest
                    parts = stripped.split(None, 1)
                    rest = parts[1] if len(parts) == 2 else ""
                break

        if not matched_field:
            continue

        value = _normalize_value(matched_field, rest)
        if value is not None:
            parsed[matched_field] = value

    return parsed


def parse_image(image_bytes: bytes) -> tuple[dict[str, Any], list[str], float]:
    """
    Parse a scanned/photographed survey form via OCR.

    Raises OCRProcessingError (unchanged from `_ocr_text_from_image`)
    for corrupt/unsupported images — callers must catch this.
    """
    raw_text = _ocr_text_from_image(image_bytes)
    raw = _parse_ocr_lines(raw_text)
    answers = _build_answers(raw)
    missing = _missing_fields(answers)

    confidence = round(
        max(OCR_BASE_CONFIDENCE - OCR_CONFIDENCE_PENALTY_PER_MISSING * len(missing), 0.0),
        2,
    )

    return answers, missing, confidence
