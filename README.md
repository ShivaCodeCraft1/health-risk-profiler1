# Health Risk Profiler

An educational, **non-diagnostic** backend service that parses lifestyle
survey answers — typed or scanned — extracts plain-English risk
factors, computes a simple, fully explainable rule-based risk score,
and generates actionable, general-wellness recommendations.

**This is a student assignment project, not a medical product.** See
[Limitations & Disclaimer](#limitations--disclaimer) below.

## Status

Feature-complete for the assignment's "AI-Powered Health Risk Profiler"
problem statement:

- Step 1 — OCR / Text Parsing (`/parse`, `/parse-image`)
- Step 2 — Factor Extraction (`/extract-factors`)
- Step 3 — Risk Classification (`/classify-risk`)
- Step 4 — Recommendations (`/recommend`)
- Combined pipeline endpoints (`/profile`, `/profile-image`) chaining
  all 4 steps in one call
- The `>50%` missing-fields guardrail, applied consistently to both
  typed and image input
- Controlled error handling for corrupt/unsupported image uploads

## Architecture

```
app/
├── main.py              # FastAPI app + all routes
├── config.py             # All constants/thresholds in one place (single source of truth)
├── schemas.py             # Pydantic request/response models
├── ocr_parser.py          # Step 1: text parsing + image OCR parsing + OCRProcessingError
├── factor_extraction.py   # Step 2: answers -> risk factors
├── risk_classifier.py     # Step 3: factors -> risk_level, score, rationale
├── recommendations.py     # Step 4: factors -> recommendations
└── pipeline.py             # Guardrail + run_full_pipeline() chaining Steps 2-4
tests/
├── test_parse.py                 # Step 1 + guardrail (typed input)
├── test_factor_extraction.py      # Step 2
├── test_risk_classifier.py         # Step 3
├── test_recommendations.py          # Step 4
├── test_pipeline.py                  # Combined /profile, /profile-image endpoints
└── test_validation.py                 # Invalid input, corrupt images, error handling
sample_requests/                        # Sample payloads/images for manual testing
```

**Data flow (both input types converge after Step 1):**

```
Typed JSON  ──► parse_text  ──┐
                                ├─► guardrail ─► extract_factors ─► classify_risk ─► generate_recommendations ─► response
Image file  ──► OCR + parse ──┘
```

If more than 50% of the expected fields (`age`, `smoker`, `exercise`,
`diet`) are missing after Step 1, the pipeline stops there and returns
the guardrail response — it never computes a risk score from
mostly-absent data.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Basic API info |
| `GET /health` | Liveness check |
| `POST /parse` | Step 1 only — typed/JSON input |
| `POST /parse-image` | Step 1 only — scanned/photographed input (OCR) |
| `POST /extract-factors` | Step 2 only |
| `POST /classify-risk` | Step 3 only |
| `POST /recommend` | Step 4 only |
| `POST /profile` | **Full pipeline (Steps 1-4), typed/JSON input** |
| `POST /profile-image` | **Full pipeline (Steps 1-4), scanned/photographed input** |

The individual step endpoints exist so each stage can be tested and
demoed in isolation, matching the exact intermediate JSON shapes shown
in the assignment. `/profile` and `/profile-image` chain all four
steps automatically for the end-to-end demo.

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Tesseract OCR — required, and NOT installed by pip

`pytesseract` (in `requirements.txt`) is just a thin Python wrapper. It
calls out to the actual **Tesseract OCR program**, which is a separate
piece of software you must install yourself — `pip install` does not
install it.

- **Windows:** Download and run the installer from the
  [UB-Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki)
  (this is the standard community Windows build). By default it
  installs to `C:\Program Files\Tesseract-OCR\tesseract.exe`. If it's
  not automatically on your `PATH`, either add that folder to `PATH`,
  or point `pytesseract` at it directly near the top of
  `app/ocr_parser.py`:
  ```python
  import pytesseract
  pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
  ```
- **macOS:** `brew install tesseract`
- **Ubuntu/Debian/most CI containers:** `sudo apt-get install tesseract-ocr`

Verify it's installed and on your `PATH` with:
```bash
tesseract --version
```
If this command fails, `/parse-image` and `/profile-image` will return
a controlled `400` error (not a crash) rather than working — see
[OCR](#ocr) below.

## Running the API

```bash
uvicorn app.main:app --reload --port 8000
```

Then open **http://localhost:8000/docs** for the interactive Swagger
UI, where every endpoint can be tried directly in the browser.

Expose it publicly for a demo/recording, if needed:
```bash
ngrok http 8000
```

## Running the tests

```bash
pytest tests/ -v
```

All tests use FastAPI's `TestClient` and run entirely offline. Image
tests generate their own small in-memory sample images at test time —
no external files or a specific installed font are required. If no
suitable TrueType font is found on the machine (which is expected and
fine on a bare Windows/CI box), the tests fall back to Pillow's
built-in bitmap font automatically.

## API Usage

### `GET /`
```bash
curl http://localhost:8000/
```
```json
{"name": "Health Risk Profiler", "version": "0.1.0", "docs": "/docs", "health_check": "/health"}
```

### `GET /health`
```bash
curl http://localhost:8000/health
```
```json
{"status": "ok"}
```

### `POST /parse` — typed/JSON survey input
```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" \
  -d '{"age":42,"smoker":true,"exercise":"rarely","diet":"high sugar"}'
```
```json
{
  "answers": {"age": 42, "smoker": true, "exercise": "rarely", "diet": "high sugar"},
  "missing_fields": [],
  "confidence": 0.97
}
```

Incomplete input (triggers the guardrail — identical response shape
for typed and image input):
```bash
curl -X POST http://localhost:8000/parse \
  -H "Content-Type: application/json" -d '{"age":42}'
```
```json
{"status": "incomplete_profile", "reason": ">50% fields missing"}
```

### `POST /parse-image` — scanned/photographed form (multipart upload)
```bash
curl -X POST http://localhost:8000/parse-image \
  -F "file=@sample_requests/sample_form_clean.png"
```
```json
{
  "answers": {"age": 42, "smoker": true, "exercise": "rarely", "diet": "high sugar"},
  "missing_fields": [],
  "confidence": 0.9
}
```

A corrupt or unrecognized file returns a controlled error instead of
crashing:
```bash
curl -X POST http://localhost:8000/parse-image \
  -F "file=@not_really_an_image.txt"
```
```json
{"status": "error", "detail": "Could not read the uploaded file as an image. Supported formats include PNG and JPEG/JPG."}
```
(HTTP status `400` in both cases above.)

### `POST /extract-factors` — Step 2, chained from Step 1's `answers`
```bash
curl -X POST http://localhost:8000/extract-factors \
  -H "Content-Type: application/json" \
  -d '{"answers":{"age":42,"smoker":true,"exercise":"rarely","diet":"high sugar"}}'
```
```json
{"factors": ["smoking", "poor diet", "low exercise"], "confidence": 1.0}
```

### `POST /classify-risk` — Step 3, chained from Step 2's `factors`
```bash
curl -X POST http://localhost:8000/classify-risk \
  -H "Content-Type: application/json" \
  -d '{"factors":["smoking","poor diet","low exercise"],"answers":{"age":42}}'
```
```json
{"risk_level": "high", "score": 88, "rationale": ["smoking", "poor diet", "low exercise", "age 40+"]}
```

### `POST /recommend` — Step 4, chained from Step 3's `risk_level` + Step 2's `factors`
```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"risk_level":"high","factors":["smoking","poor diet","low exercise"]}'
```
```json
{
  "risk_level": "high",
  "factors": ["smoking", "poor diet", "low exercise"],
  "recommendations": ["Quit smoking", "Reduce sugar", "Walk 30 mins daily"],
  "status": "ok"
}
```
This matches the assignment's Step 4 sample output exactly.

### `POST /profile` — full pipeline in one call, typed/JSON input
```bash
curl -X POST http://localhost:8000/profile \
  -H "Content-Type: application/json" \
  -d '{"age":42,"smoker":true,"exercise":"rarely","diet":"high sugar"}'
```
```json
{
  "risk_level": "high",
  "factors": ["smoking", "poor diet", "low exercise"],
  "recommendations": ["Quit smoking", "Reduce sugar", "Walk 30 mins daily"],
  "status": "ok"
}
```
With sparse input, the exact same guardrail response as `/parse`:
```json
{"status": "incomplete_profile", "reason": ">50% fields missing"}
```

### `POST /profile-image` — full pipeline in one call, scanned form
```bash
curl -X POST http://localhost:8000/profile-image \
  -F "file=@sample_requests/sample_form_clean.png"
```
```json
{
  "risk_level": "high",
  "factors": ["smoking", "poor diet", "low exercise"],
  "recommendations": ["Quit smoking", "Reduce sugar", "Walk 30 mins daily"],
  "status": "ok"
}
```

## Input validation

`age` (when provided) must be an integer between 18 and 120 inclusive.
Values outside that range, or non-numeric values, return a controlled
`HTTP 422` with Pydantic's validation error details — they are never
silently accepted into risk scoring.

## Risk scoring — how it actually works

This is a **fixed, rule-based, deterministic formula** — no machine
learning, no trained weights, nothing probabilistic. Every number below
lives in `app/config.py` in one place:

| Factor | Points |
|---|---|
| `smoking` | 35 |
| `poor diet` | 25 |
| `low exercise` | 20 |
| Age 40+ | +8 |
| Age 60+ | +15 (instead of +8) |

Score is capped at 100, then bucketed:

| Score | `risk_level` |
|---|---|
| 0–29 | `low` |
| 30–59 | `medium` |
| 60–100 | `high` |

`rationale` always lists exactly which of the above contributed, so
every score is fully traceable back to specific answers — there is no
hidden logic. These exact point values aren't specified anywhere in
the assignment; they're a deliberately simple starting point chosen
for transparency, and can be re-tuned by editing `app/config.py` alone.

## Guardrail behavior

Implemented in `app/pipeline.py::is_incomplete_profile`, using the
`EXPECTED_FIELDS` and `MISSING_FIELD_THRESHOLD` constants from
`app/config.py`. Applied identically regardless of input source:

- Typed JSON with `> 50%` of `age`/`smoker`/`exercise`/`diet` missing → guardrail
- A scanned image where OCR could confidently extract `≤ 50%` of those
  fields → same guardrail

In both cases the response is exactly:
```json
{"status": "incomplete_profile", "reason": ">50% fields missing"}
```
No risk score, no factors, and no recommendations are ever computed
from a profile that fails this check.

## OCR

Supports PNG and JPEG/JPG (anything Pillow can open). Images are
converted to RGB before OCR to normalize palette/CMYK/RGBA inputs.

Text extraction from the OCR'd output uses **rule-based OCR error
correction using known common OCR variants** — specifically:
- tolerating a missing colon after a field name ("Age 42" as well as "Age: 42")
- a loose prefix match on the first several characters of a field name,
  to tolerate a couple of misread letters (e.g. "Exercise" OCR'd as
  "Brercise" still matches)
- a small fixed list of yes/no word variants (`yes`/`y`/`true`/`1`,
  `no`/`n`/`false`/`0`)

This is intentionally simple and fully inspectable in
`app/ocr_parser.py::_parse_ocr_lines` — it is **not** a general
fuzzy-matching or edit-distance algorithm, and no such library is used.

**Error handling:** a corrupt file, an unsupported format, or a missing
Tesseract binary all raise a single `OCRProcessingError`, which
`app/main.py` catches and turns into a controlled `HTTP 400` response.
The API does not crash on bad image input.

## Sample requests

In `sample_requests/`:

| File | Purpose |
|---|---|
| `healthy_profile.json` | Complete input, expected to score `low` risk |
| `high_risk_profile.json` | Complete input, expected to score `high` risk |
| `text_input_incomplete.json` | Triggers the guardrail |
| `invalid_profile.json` | Non-coercible types (`age`, `smoker`) — expect `422` |
| `sample_form_clean.png` | Clean scanned form — full OCR success |
| `sample_form.png` | Deliberately noisy scanned form — demonstrates partial OCR recovery + `missing_fields` |

## Limitations & Disclaimer

- **This is not a medical device and has no clinical validation.** The
  risk score is a simple, deterministic, rule-based educational
  exercise — it is not derived from any medical study, clinical
  dataset, or trained model, and must not be used for real health
  decisions.
- The recognized field set (`age`, `smoker`, `exercise`, `diet`) and
  the risk factors/points are intentionally minimal, matching only
  what the assignment's sample input/output specifies.
- OCR accuracy depends on image quality; very noisy or low-resolution
  scans may under-extract fields (correctly reported via
  `missing_fields`, not silently guessed).
- No database or persistence layer — every request is stateless.
- No authentication — not intended for production/public deployment
  as-is.
