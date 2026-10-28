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
    # Synthetic test fixture (NOT measurements): 270 -> 140 => 130 kgCO2e/year.
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


def test_equal_annualized_activity_produces_valid_zero_reduction() -> None:
    body = {
        "baseline": [activity("grid electricity", 12, factor=0.5, period="month")],
        "projected": [activity("grid electricity", 144, factor=0.5, period="year")],
    }
    response = client.post("/api/v1/carbon/calculate", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["baseline_emissions_kgco2e_per_year"] == 72
    assert result["projected_emissions_kgco2e_per_year"] == 72
    assert result["reduction_kgco2e_per_year"] == 0
    assert result["reduction_percent"] == 0
    assert result["direction"] == "no_change"


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


@pytest.mark.parametrize("missing_side", ["baseline", "projected"])
def test_missing_baseline_or_projected_activity_is_rejected(missing_side: str) -> None:
    body = {"baseline": [activity("x", 1)], "projected": [activity("x", 1)]}
    body[missing_side] = []
    response = client.post("/api/v1/carbon/calculate", json=body)
    assert response.status_code == 422
    assert missing_side in response.text


@pytest.mark.parametrize("missing_field", ["quantity", "quantity_unit", "emission_factor_kgco2e_per_unit", "factor_source"])
def test_missing_activity_inputs_are_rejected_not_defaulted(missing_field: str) -> None:
    incomplete = activity("x", 1)
    del incomplete[missing_field]
    response = client.post(
        "/api/v1/carbon/calculate",
        json={"baseline": [incomplete], "projected": [activity("x", 1)]},
    )
    assert response.status_code == 422
    assert missing_field in response.text


def test_overflowing_annualized_inputs_are_rejected_as_invalid() -> None:
    body = {
        "baseline": [activity("x", 1e308, period="day")],
        "projected": [activity("x", 0)],
    }
    response = client.post("/api/v1/carbon/calculate", json=body)
    assert response.status_code == 422
    assert "non-finite annual emissions" in response.json()["detail"]


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
