import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.main import app

client = TestClient(app)

# Cross-platform font discovery: try a handful of common installed-font
# locations across Windows, macOS, and Linux. None of these paths are
# required to exist — if nothing is found, we fall back to Pillow's
# built-in bitmap font (scaled up), so the test never fails purely
# because of a missing system font.
_CANDIDATE_FONT_PATHS = [
    # Windows
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    # Linux (common distro locations; not assumed to exist)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_test_font(size: int = 28) -> ImageFont.ImageFont:
    """Find a usable font for rendering test images, without assuming
    any specific OS or that any particular font is installed."""
    for path in _CANDIDATE_FONT_PATHS:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue

    # No system TrueType font found (e.g. a minimal CI/Windows box).
    # Pillow's default bitmap font supports a `size` argument since
    # Pillow 10.1 — this keeps the test fully self-contained.
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Very old Pillow without the `size` kwarg — still usable,
        # just renders smaller.
        return ImageFont.load_default()


def _make_form_image(lines: list[str]) -> bytes:
    font = _load_test_font(28)
    img = Image.new("RGB", (500, 40 + 45 * len(lines)), color="white")
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        draw.text((20, 20 + i * 45), line, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_profile_full_pipeline_from_text():
    payload = {"age": 42, "smoker": True, "exercise": "rarely", "diet": "high sugar"}
    response = client.post("/profile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "risk_level": "high",
        "factors": ["smoking", "poor diet", "low exercise"],
        "recommendations": ["Quit smoking", "Reduce sugar", "Walk 30 mins daily"],
        "status": "ok",
    }


def test_profile_triggers_guardrail_from_text():
    payload = {"age": 42}  # only 1/4 fields -> 75% missing
    response = client.post("/profile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "incomplete_profile", "reason": ">50% fields missing"}


def test_profile_healthy_answers_low_risk():
    payload = {"age": 25, "smoker": False, "exercise": "daily", "diet": "balanced"}
    response = client.post("/profile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "low"
    assert data["factors"] == []
    assert data["recommendations"] == []
    assert data["status"] == "ok"


def test_profile_image_full_pipeline():
    image_bytes = _make_form_image(["Age: 42", "Smoker: yes", "Exercise: rarely", "Diet: high sugar"])
    response = client.post(
        "/profile-image", files={"file": ("form.png", image_bytes, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "high"
    assert "smoking" in data["factors"]
    assert data["status"] == "ok"


def test_profile_image_triggers_guardrail():
    image_bytes = _make_form_image(["Age: 42"])  # only 1 field legible -> guardrail
    response = client.post(
        "/profile-image", files={"file": ("form.png", image_bytes, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "incomplete_profile", "reason": ">50% fields missing"}
