from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_text_complete():
    payload = {
        "age": 42,
        "smoker": True,
        "exercise": "rarely",
        "diet": "high sugar",
    }
    response = client.post("/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["answers"] == payload
    assert data["missing_fields"] == []
    assert 0 <= data["confidence"] <= 1


def test_parse_text_triggers_guardrail():
    # Only 1 of 4 expected fields present -> 75% missing -> guardrail
    payload = {"age": 42}
    response = client.post("/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "incomplete_profile"
    assert data["reason"] == ">50% fields missing"


def test_parse_text_partial_but_under_threshold():
    # 2 of 4 fields present -> exactly 50% missing -> NOT > 50%, guardrail should not fire
    payload = {"age": 42, "smoker": True}
    response = client.post("/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answers" in data
    assert data["missing_fields"] == ["exercise", "diet"]
