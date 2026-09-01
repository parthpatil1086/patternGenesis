from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_endpoint():
    response = client.post("/api/generate", json={"grammar": {"grammar_version": "1.0"}, "parameters": {"symmetry_order": 4, "grid_rows": 3, "grid_columns": 3, "spacing": 40}})
    assert response.status_code == 200
    payload = response.json()
    assert payload["parameters"]["symmetry_order"] == 4
    assert payload["grammar"]["symmetry"]["order"] == 4


def test_variations_endpoint():
    response = client.post("/api/variations", json={"grammar": {"grammar_version": "1.0"}, "parameters": {"symmetry_order": 4, "grid_rows": 2, "grid_columns": 2, "spacing": 40}})
    assert response.status_code == 200
    assert "variations" in response.json()
