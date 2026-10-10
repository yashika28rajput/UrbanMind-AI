from fastapi.testclient import TestClient

from app.database.urban_memory_store import SessionLocal
from app.phase10.repository import ScenarioRecord, ScenarioRequestRecord
from app.main import app

client = TestClient(app)


def _demo_payload() -> dict[str, object]:
    return {
        "scenario_name": "Illustrative bus electrification comparison",
        "annual_vehicle_km": 1_000_000,
        "diesel_litres_per_vehicle_km": 0.35,
        "electric_kwh_per_vehicle_km": 1.2,
        "diesel_emission_factor_kg_co2_per_litre": 2.68,
        "electricity_emission_factor_kg_co2_per_kwh": 0.65,
        "baseline_period_start": "2023-01-01",
        "baseline_period_end": "2023-12-31",
        "project_period_start": "2024-01-01",
        "project_period_end": "2024-12-31",
        "activity_source": "Illustrative demonstration assumptions",
        "activity_reference": "User-editable demo defaults; not observed Delhi records",
        "input_classification": "Illustrative",
        "diesel_factor": {
            "source": "Illustrative demonstration assumption",
            "version": "Demo assumption v1",
            "reference": "Not an official factor",
            "status": "Illustrative",
        },
        "electricity_factor": {
            "source": "Illustrative demonstration assumption",
            "version": "Demo assumption v1",
            "reference": "Not an official factor",
            "status": "Illustrative",
        },
    }


def _remove_saved_scenario(scenario_id: str | None) -> None:
    if not scenario_id:
        return
    with SessionLocal() as session:
        scenario = session.query(ScenarioRecord).filter_by(scenario_id=scenario_id).one_or_none()
        if scenario is None:
            return
        request_record = session.get(ScenarioRequestRecord, scenario.request_id)
        session.delete(scenario)
        if request_record is not None:
            session.delete(request_record)
        session.commit()


def test_calculates_illustrative_transport_scenario_with_units_and_provenance() -> None:
    response = client.post("/api/v1/carbon/scenarios/calculate", json=_demo_payload())

    assert response.status_code == 200, response.text
    result = response.json()
    try:
        assert result["result_classification"] == "SIMULATED"
        assert result["display_label"] == "SIMULATED SCENARIO — NOT MEASURED"
        assert result["unit"] == "tCO2/year"
        assert result["baseline_emissions_tco2_per_year"] == 938
        assert result["project_emissions_tco2_per_year"] == 780
        assert result["avoided_emissions_tco2_per_year"] == 158
        assert result["percentage_change"] == -16.844349680170576
        assert result["assumptions"]["diesel_factor"]["status"] == "Illustrative"
        assert "Illustrative demonstration assumptions" in result["assumptions"]["activity_source"]
        saved = client.get(f"/api/v1/scenarios/{result['scenario_id']}")
        assert saved.status_code == 200
        assert saved.json()["status"] == "SIMULATED"
        assert saved.json()["expected_impacts"] is None
        assert saved.json()["provenance"]["carbon_scenario_result"]["result_classification"] == "SIMULATED"
        assert saved.json()["provenance"]["carbon_scenario_result"]["scenario_id"] == result["scenario_id"]
    finally:
        _remove_saved_scenario(result.get("scenario_id"))


def test_signed_result_can_show_emissions_increase_and_is_not_persisted_to_city_metrics() -> None:
    payload = _demo_payload()
    payload["electricity_emission_factor_kg_co2_per_kwh"] = 1.0
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)

    assert response.status_code == 200, response.text
    result = response.json()
    try:
        assert result["avoided_emissions_tco2_per_year"] == -262
        summary = client.get("/api/v1/digital-twin/summary").json()["summary"]
        assert summary.get("carbon_reduction") is None
        assert summary["carbon_reduction_availability_reason"]
    finally:
        _remove_saved_scenario(result.get("scenario_id"))


def test_rejects_nonpositive_factors_and_missing_required_fields() -> None:
    payload = _demo_payload()
    payload["diesel_emission_factor_kg_co2_per_litre"] = 0
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)
    assert response.status_code == 422
    assert "greater than 0" in response.text

    payload = _demo_payload()
    payload.pop("annual_vehicle_km")
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)
    assert response.status_code == 422
    assert "annual_vehicle_km" in response.text


def test_rejects_finite_inputs_that_overflow_the_calculation() -> None:
    payload = _demo_payload()
    payload["annual_vehicle_km"] = 1.7e308
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)

    assert response.status_code == 422
    assert "non-finite result" in response.text


def test_rejects_nonannual_period_and_demo_data_relabelled_as_measured() -> None:
    payload = _demo_payload()
    payload["baseline_period_end"] = "2023-06-30"
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)
    assert response.status_code == 422
    assert "one annual reporting period" in response.text

    payload = _demo_payload()
    payload["baseline_period_start"] = "2023-01-01"
    payload["baseline_period_end"] = "2023-12-31"
    payload["project_period_start"] = "2023-12-01"
    payload["project_period_end"] = "2024-11-30"
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)
    assert response.status_code == 422
    assert "must end before the project reporting period starts" in response.text

    payload = _demo_payload()
    payload["input_classification"] = "Measured"
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)
    assert response.status_code == 422
    assert "Replace the illustrative activity source" in response.text


def test_measured_classification_requires_activity_evidence_and_verified_factors() -> None:
    payload = _demo_payload()
    payload["input_classification"] = "Measured"
    payload["activity_source"] = "Fleet fuel log and charger meter records"
    payload["activity_reference"] = "dataset://validated-pilot-records"
    payload["diesel_factor"] = {
        "source": "Verified factor publication",
        "version": "2024",
        "reference": "https://example.invalid/factor-source",
        "status": "Verified",
    }
    payload["electricity_factor"] = {
        "source": "Verified factor publication",
        "version": "2024",
        "reference": "https://example.invalid/grid-factor",
        "status": "Verified",
    }
    payload["diesel_factor"]["status"] = "Unverified"
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)
    assert response.status_code == 422
    assert "verified provenance" in response.text
    payload["diesel_factor"]["status"] = "Verified"
    response = client.post("/api/v1/carbon/scenarios/calculate", json=payload)

    assert response.status_code == 200, response.text
    result = response.json()
    try:
        assert result["result_classification"] == "MEASURED"
        assert result["display_label"] == "MEASURED SCENARIO"
    finally:
        _remove_saved_scenario(result.get("scenario_id"))
