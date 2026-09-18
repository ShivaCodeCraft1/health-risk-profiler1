from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_classify_risk_high():
    payload = {
        "factors": ["smoking", "poor diet", "low exercise"],
        "answers": {"age": 42},
    }
    response = client.post("/classify-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "high"
    assert data["score"] > 59
    assert "smoking" in data["rationale"]
    assert "poor diet" in data["rationale"]
    assert "low exercise" in data["rationale"]
    assert "age 40+" in data["rationale"]


def test_classify_risk_low_no_factors():
    payload = {"factors": [], "answers": {"age": 25}}
    response = client.post("/classify-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "low"
    assert data["score"] == 0
    assert data["rationale"] == []


def test_classify_risk_medium_two_factors():
    payload = {"factors": ["poor diet", "low exercise"], "answers": {"age": 30}}
    response = client.post("/classify-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "medium"
    assert data["score"] == 45


def test_classify_risk_score_capped_at_100():
    payload = {
        "factors": ["smoking", "poor diet", "low exercise"],
        "answers": {"age": 65},
    }
    response = client.post("/classify-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["score"] <= 100
