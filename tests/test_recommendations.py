from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_recommend_matches_assignment_sample():
    payload = {
        "risk_level": "high",
        "factors": ["smoking", "poor diet", "low exercise"],
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "risk_level": "high",
        "factors": ["smoking", "poor diet", "low exercise"],
        "recommendations": ["Quit smoking", "Reduce sugar", "Walk 30 mins daily"],
        "status": "ok",
    }


def test_recommend_no_factors_no_recommendations():
    payload = {"risk_level": "low", "factors": []}
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"] == []
    assert data["status"] == "ok"


def test_recommend_unknown_factor_skipped():
    payload = {"risk_level": "medium", "factors": ["smoking", "unknown factor"]}
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"] == ["Quit smoking"]
