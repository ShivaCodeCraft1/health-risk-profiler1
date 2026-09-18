from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_extract_factors_all_risky():
    payload = {
        "answers": {
            "age": 42,
            "smoker": True,
            "exercise": "rarely",
            "diet": "high sugar",
        }
    }
    response = client.post("/extract-factors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert set(data["factors"]) == {"smoking", "poor diet", "low exercise"}
    assert 0 <= data["confidence"] <= 1


def test_extract_factors_healthy_answers_no_factors():
    payload = {
        "answers": {
            "smoker": False,
            "exercise": "daily",
            "diet": "balanced",
        }
    }
    response = client.post("/extract-factors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["factors"] == []


def test_extract_factors_partial_answers():
    # Only smoker present -> only that field is evaluable
    payload = {"answers": {"smoker": True}}
    response = client.post("/extract-factors", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["factors"] == ["smoking"]
    assert data["confidence"] < 1.0  # fewer evaluable fields -> lower confidence
