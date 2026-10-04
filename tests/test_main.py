from uuid import uuid4

from fastapi.testclient import TestClient

from app.database.urban_memory_store import SessionLocal, UrbanMemory
from app.main import app

client = TestClient(app)


def _remove_test_memory(memory_id: str) -> None:
    with SessionLocal() as session:
        memory = session.get(UrbanMemory, memory_id)
        if memory is not None:
            session.delete(memory)
            session.commit()


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "UrbanMind AI"
    assert data["phase"] == "PHASE 13 — Explainability and decision pipeline"


def test_aqi_prediction_endpoint() -> None:
    payload = {
        "features": {
            "pm25": 53.0,
            "pm10": 134.0,
            "no2": 1.75,
            "o3": 7.8,
            "co": 0.51,
            "so2": 2.5,
            "pm25_index": 21.2,
            "pm10_index": 31.16279069767442,
            "no2_index": 0.4375,
            "o3_index": 1.95,
            "so2_index": 0.625,
            "co_index": 1.02,
            "pm25_lag_1": 47.0,
            "pm10_lag_1": 108.0,
            "no2_lag_1": 1.1,
            "o3_lag_1": 5.85,
            "AQI_lag_1": 25.116279069767444,
            "hour": 2,
            "day": 1,
            "day_of_week": 2,
            "month": 7,
        }
    }

    response = client.post("/api/v1/predict/aqi", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "predicted_value" in data
    assert data["target"] == "AQI"


def test_urban_heat_prediction_endpoint() -> None:
    payload = {
        "features": {
            "TOT_P": 66035,
            "No_HH": 12384,
            "TOT_M": 35015,
            "TOT_F": 31020,
            "P_06": 8913,
            "P_LIT": 46492,
            "P_ILL": 19543,
            "water": 0.0,
            "trees": 0.0,
            "grass": 0.0,
            "flooded_vegetation": 0.0,
            "crops": 0.0,
            "shrub_and_scrub": 0.0,
            "built": 0.3527955170252589,
            "bare": 0.6472044829747396,
            "snow_and_ice": 0.0,
            "vegetation": 0.0,
            "built_environment": 0.3527955170252589,
            "water_surface": 0.0,
            "road_segment_count": 1509,
            "oneway_road_segments": 25,
            "total_road_length_km": 75.029463919992,
            "primary_road_length_km": 0.0,
            "secondary_road_length_km": 0.0,
            "tertiary_road_length_km": 0.6964067418333,
            "residential_road_length_km": 69.16671594524286,
            "major_road_length_km": 4.806991765278938,
            "average_road_segment_length_m": 49.72131472497813,
            "oneway_fraction": 0.0165672630881378,
            "road_density_km_per_km2": 38.822535097399935,
            "major_road_density_km_per_km2": 2.4872842850037777,
            "traffic_pressure_index": 0.1236618923854595,
            "built_pressure_index": 0.2655990269624398,
            "heat_pressure_index": 0.1346373231924354,
            "vegetation_mitigation_index": 0.0,
            "emission_pressure_index": 0.1695356620006464,
            "green_cover_intervention_potential": 0.0596047988490793,
            "urban_forest_potential": 0.0210283058271474,
            "roadside_greening_potential": 0.0187835278203737,
            "cool_roof_intervention_potential": 0.2600911633659034,
            "water_body_restoration_potential": 0.7372292186674295,
            "heat_mitigation_potential": 0.7372292186674295,
            "air_pollution_mitigation_potential": 0.1695356620006464,
            "sustainable_mobility_potential": 0.1216131532803326,
            "urban_intervention_potential": 0.1179082398693838,
        }
    }

    response = client.post("/api/v1/predict/urban-heat", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "predicted_value" in data
    assert data["target"] == "mean_LST_C"


def test_green_cover_prediction_endpoint() -> None:
    payload = {
        "features": {
            "trees": 0.1398035476,
            "grass": 0.0,
            "flooded_vegetation": 0.0,
            "crops": 3.3462055079e-05,
            "shrub_and_scrub": 0.0,
            "vegetation": 0.1398035476,
            "built": 0.5762312855,
        }
    }

    response = client.post("/api/v1/predict/green-cover", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["target"] == "green_cover_percent"
    assert "predicted_value" in data


def test_carbon_reduction_endpoint() -> None:
    payload = {
        "features": {
            "green_cover_percent": 14.0,
            "emission_pressure_index": 0.25981286,
            "urban_intervention_potential": 0.1346882484,
        }
    }

    response = client.post("/api/v1/predict/carbon-reduction", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["target"] == "CO2_reduction_tons"
    assert "predicted_value" in data


def test_health_risk_endpoint() -> None:
    payload = {
        "features": {
            "AQI_risk_index": 0.0498146572,
            "heat_risk_index": 0.2947327505,
            "population_vulnerability_index": 0.1663884146,
            "health_exposure_score": 16.6388414563,
        }
    }

    response = client.post("/api/v1/predict/health-risk", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["target"] == "health_risk_score"
    assert "predicted_value" in data


def test_digital_twin_summary_endpoint() -> None:
    response = client.get("/api/v1/digital-twin/summary")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["city"] == "Delhi"
    assert data["phase"] == "PHASE 5 — Urban Digital Twin"
    assert "summary" in data


def test_digital_twin_ward_endpoint() -> None:
    response = client.get("/api/v1/digital-twin/ward/80")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ward_no"] == 80
    assert data["city"] == "Delhi"


def test_urban_memory_write_list_and_vector_search() -> None:
    token = str(uuid4())
    payload = {
        "memory_type": "simulation",
        "city": "Delhi",
        "zone": f"Ward_{token}",
        "title": f"Green corridor simulation {token}",
        "content": f"Successful lower temperature outcome from urban forest intervention {token}",
        "structured_data": {"intervention": "urban_forest", "estimated_heat_reduction_c": 1.2},
        "outcome": "success",
    }

    created = client.post("/api/v1/memory/memories", json=payload)
    assert created.status_code == 201, created.text
    created_data = created.json()
    assert created_data["type"] == "simulation"
    assert created_data["outcome"] == "success"

    outcome = client.patch(
        f"/api/v1/memory/memories/{created_data['id']}/outcome",
        json={
            "outcome": "failure",
            "outcome_notes": "Follow-up monitoring found the predicted cooling effect did not occur.",
        },
    )
    assert outcome.status_code == 200, outcome.text
    assert outcome.json()["outcome"] == "failure"
    assert "Follow-up monitoring" in outcome.json()["content"]

    listed = client.get(
        "/api/v1/memory/memories",
        params={"memory_type": "simulation", "city": "Delhi", "zone": payload["zone"]},
    )
    assert listed.status_code == 200, listed.text
    assert any(memory["id"] == created_data["id"] for memory in listed.json()["memories"])

    searched = client.post(
        "/api/v1/memory/search",
        json={
            "query": f"urban forest intervention lower temperature {token}",
            "memory_type": "simulation",
            "city": "Delhi",
            "outcome": "failure",
            "limit": 5,
        },
    )
    assert searched.status_code == 200, searched.text
    assert searched.json()["results"][0]["id"] == created_data["id"]
    _remove_test_memory(created_data["id"])


def test_urban_memory_source_reference_is_idempotent() -> None:
    token = str(uuid4())
    payload = {
        "memory_type": "recommendation",
        "city": "Delhi",
        "title": f"Ward recommendation {token}",
        "content": "Install green infrastructure to reduce heat exposure.",
        "structured_data": {"intervention": "green_cover"},
        "outcome": "unknown",
        "source_ref": f"test:{token}",
    }

    first = client.post("/api/v1/memory/memories", json=payload)
    second = client.post("/api/v1/memory/memories", json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    _remove_test_memory(first.json()["id"])


def test_urban_memory_status_endpoint() -> None:
    response = client.get("/api/v1/memory/status")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "ready"
    assert data["database_backend"] in {"sqlite", "postgresql"}
    assert data["memory_count"] >= 0
