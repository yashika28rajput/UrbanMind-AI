from fastapi.testclient import TestClient
import pandas as pd

from app.main import app
from app.config import settings
from app.digital_twin import service as digital_twin_service
from app.services.dashboard_auth import hash_password, token_subject, verify_password

client = TestClient(app)


def test_digital_twin_preserves_zero_and_missing_environmental_values(monkeypatch, tmp_path) -> None:
    environment = pd.DataFrame({
        "Ward_No": [1, 2],
        "Ward_Name": ["Zero Ward", "Missing Ward"],
        "final_AQI": [0.0, float("nan")],
        "mean_LST_C": [0.0, float("nan")],
        "vegetation_risk_index": [1.0, float("nan")],
        "traffic_risk_index": [0.0, float("nan")],
    })
    health = pd.DataFrame({
        "Ward_No": [1, 2],
        "Ward_Name": ["Zero Ward", "Missing Ward"],
        "TOT_P": [0.0, float("nan")],
        "health_exposure_score": [0.0, float("nan")],
        "population_vulnerability_index": [0.0, float("nan")],
    })
    frames = iter([environment, health])
    monkeypatch.setattr(digital_twin_service.pd, "read_csv", lambda _path: next(frames))
    monkeypatch.setattr(digital_twin_service, "SNAPSHOT_PATH", tmp_path / "digital-twin.json")

    model = digital_twin_service.build_virtual_city_model()

    zero_ward, missing_ward = model["wards"]
    assert zero_ward["aqi"] == 0
    assert zero_ward["temperature"] == 0
    assert zero_ward["green_cover"] == 0
    assert zero_ward["health_risk"] == 0
    assert zero_ward["population"] == 0
    assert missing_ward["aqi"] is None
    assert missing_ward["temperature"] is None
    assert missing_ward["green_cover"] is None
    assert missing_ward["health_risk"] is None
    assert missing_ward["population"] is None
    assert model["summary"]["average_aqi"] == 0
    assert model["summary"]["average_temperature_c"] == 0


def test_dashboard_ward_geojson_uses_real_ward_metrics() -> None:
    response = client.get("/api/v1/digital-twin/wards/geojson")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 272
    properties = payload["features"][0]["properties"]
    assert properties["ward_no"] > 0
    assert isinstance(properties["aqi"], (int, float))
    assert isinstance(properties["population"], int)


def test_system_status_reports_live_service_states(monkeypatch) -> None:
    monkeypatch.setattr(settings, "QDRANT_URL", None)

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["overall_status"] in {"HEALTHY", "DEGRADED", "UNAVAILABLE"}
    assert {"fastapi", "database", "qdrant", "rag", "ml_models", "digital_twin"} <= set(payload["components"])
    assert payload["components"]["fastapi"]["status"] == "HEALTHY"
    assert payload["components"]["qdrant"]["status"] == "NOT_CONFIGURED"
    assert payload["components"]["rag"]["mode"] == "fallback"
    assert payload["overall_status"] == "DEGRADED"


def test_rag_health_identifies_fallback_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "QDRANT_URL", None)

    response = client.get("/api/v1/rag/health")

    assert response.status_code == 200
    assert response.json()["mode"] == "fallback"
    assert response.json()["status"] == "DEGRADED"


def test_password_hash_and_signed_token(monkeypatch) -> None:
    encoded = hash_password("correct horse battery staple", salt="fixed-test-salt")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)

    monkeypatch.setattr(settings, "AUTH_USERNAME", "planner")
    monkeypatch.setattr(settings, "AUTH_PASSWORD_HASH", encoded)
    monkeypatch.setattr(settings, "AUTH_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
    from app.services.dashboard_auth import create_access_token

    token = create_access_token("planner")
    assert token_subject(token) == "planner"
    assert token_subject(token + "tampered") is None


def test_required_auth_protects_dashboard_apis(monkeypatch) -> None:
    encoded = hash_password("dashboard-password", salt="dashboard-test-salt")
    monkeypatch.setattr(settings, "AUTH_REQUIRED", True)
    monkeypatch.setattr(settings, "AUTH_USERNAME", "planner")
    monkeypatch.setattr(settings, "AUTH_PASSWORD_HASH", encoded)
    monkeypatch.setattr(settings, "AUTH_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")

    preflight = client.options(
        "/api/v1/digital-twin/summary",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert preflight.status_code == 200
    assert client.get("/api/v1/digital-twin/summary").status_code == 401
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "planner", "password": "dashboard-password"},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).json() == {"username": "planner"}
    assert client.get("/api/v1/digital-twin/summary", headers=headers).status_code == 200


def test_rag_query_discloses_retrieval_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "QDRANT_URL", None)

    response = client.post(
        "/api/v1/rag/query",
        json={"query": "urban air quality and respiratory health", "city": "Delhi"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["retrieval_mode"] == "fallback"
    assert response.json()["sources"]
