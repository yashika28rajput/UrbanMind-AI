import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SRC = "Test fixture factor (not a validated Delhi value)"


def activity(name, quantity, unit="kWh", factor=1.0, period="year", source=SRC):
    return {
        "name": name,
        "quantity": quantity,
        "quantity_unit": unit,
        "period": period,
        "emission_factor_kgco2e_per_unit": factor,
        "factor_source": source,
    }


def test_explicit_example_inputs_give_expected_reduction() -> None:
    # Explicitly supplied test inputs (NOT measurements): 270 -> 140 => 130 kgCO2e/year.
    body = {
        "baseline": [activity("grid electricity", 300, factor=0.5), activity("diesel", 60, "litre", 2.0)],
        "projected": [activity("grid electricity", 160, factor=0.5), activity("diesel", 30, "litre", 2.0)],
    }
    response = client.post("/api/v1/carbon/calculate", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["baseline_emissions_kgco2e_per_year"] == 270
    assert data["projected_emissions_kgco2e_per_year"] == 140
    assert data["reduction_kgco2e_per_year"] == 130
    assert data["evidence_type"] == "user_supplied_inputs"
    assert data["direction"] == "reduction"


def test_monthly_quantities_are_annualised() -> None:
    body = {"baseline": [activity("x", 10, period="month", factor=2.0)], "projected": [activity("x", 0)]}
    data = client.post("/api/v1/carbon/calculate", json=body).json()
    assert data["baseline_emissions_kgco2e_per_year"] == 240


@pytest.mark.parametrize(
    "mutation",
    [
        {"quantity": -1},
        {"emission_factor_kgco2e_per_unit": -0.1},
        {"factor_source": ""},
        {"period": "decade"},
    ],
)
def test_invalid_inputs_are_rejected(mutation) -> None:
    bad = {**activity("x", 1), **mutation}
    response = client.post("/api/v1/carbon/calculate", json={"baseline": [bad], "projected": [activity("x", 1)]})
    assert response.status_code == 422


def test_missing_emission_factor_is_rejected_not_defaulted() -> None:
    bad = activity("x", 1)
    del bad["emission_factor_kgco2e_per_unit"]
    response = client.post("/api/v1/carbon/calculate", json={"baseline": [bad], "projected": [activity("x", 1)]})
    assert response.status_code == 422


def test_unit_mismatch_between_baseline_and_projected_is_rejected() -> None:
    body = {"baseline": [activity("fuel", 10, "litre")], "projected": [activity("fuel", 10, "kWh")]}
    response = client.post("/api/v1/carbon/calculate", json=body)
    assert response.status_code == 422
    assert "not be comparable" in response.json()["detail"]


def test_increase_and_zero_baseline_are_reported_honestly() -> None:
    body = {"baseline": [activity("x", 0)], "projected": [activity("x", 5)]}
    data = client.post("/api/v1/carbon/calculate", json=body).json()
    assert data["direction"] == "increase"
    assert data["reduction_percent"] is None
    assert data["reduction_percent_note"]
