import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ward_carbon_data

client = TestClient(app)


def _rewrite_csv(source_path: Path, destination: Path, mutate) -> None:
    with source_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        rows = list(reader)
        fieldnames = reader.fieldnames
    mutate(rows)
    with destination.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_annual_endpoint_maps_real_csv_schema_and_keeps_methodology_paths_cwd_independent(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    response = client.get("/api/v1/carbon/wards/annual")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["wards"]) == 272
    assert payload["metadata"]["estimate_label"] == "MODELLED 2021 ROAD-TRAFFIC CO2"
    assert payload["metadata"]["unit"] == "tonnes CO2/year"
    assert payload["metadata"]["methodology_file"] == "CHETNA_Road_Delhi_CO2_methodology.md"
    # CSV primary estimate, ward key, coverage percentage, and flag are mapped explicitly.
    csv_record = next(row for row in csv.DictReader(ward_carbon_data.ANNUAL_CSV_PATH.open(encoding="utf-8-sig")) if row["ward_id"] == "80")
    api_record = next(row for row in payload["wards"] if row["ward_id"] == 80)
    assert api_record["ward_name"] == csv_record["ward_name"]
    assert api_record["annual_co2_tonnes"] == pytest.approx(float(csv_record["annual_co2_tonnes"]))
    assert api_record["valid_area_coverage_pct"] == pytest.approx(float(csv_record["valid_area_coverage_pct"]))
    assert api_record["coverage_flag"] == csv_record["coverage_flag"]
    assert sum(row["coverage_flag"] == "PARTIAL_LT90%" for row in payload["wards"]) == 15


def test_missing_or_invalid_emissions_are_unavailable_not_zero(monkeypatch, tmp_path) -> None:
    destination = tmp_path / "annual.csv"

    def make_emissions_invalid(rows):
        rows[0]["annual_co2_tonnes"] = ""
        rows[1]["annual_co2_tonnes"] = "not-a-number"

    _rewrite_csv(ward_carbon_data.ANNUAL_CSV_PATH, destination, make_emissions_invalid)
    monkeypatch.setattr(ward_carbon_data, "ANNUAL_CSV_PATH", destination)

    records = ward_carbon_data.load_annual_ward_carbon()["wards"]
    assert records[0]["annual_co2_tonnes"] is None
    assert records[1]["annual_co2_tonnes"] is None


@pytest.mark.parametrize("invalid_id", ["", "not-an-id", "0", "1.5", "273"])
def test_invalid_ward_ids_fail_without_dropping_rows(monkeypatch, tmp_path, invalid_id) -> None:
    destination = tmp_path / "annual.csv"
    _rewrite_csv(ward_carbon_data.ANNUAL_CSV_PATH, destination, lambda rows: rows[0].update(ward_id=invalid_id))
    monkeypatch.setattr(ward_carbon_data, "ANNUAL_CSV_PATH", destination)

    with pytest.raises(ValueError, match="Invalid ward_id"):
        ward_carbon_data.load_annual_ward_carbon()


def test_duplicate_ward_ids_fail_without_dropping_rows(monkeypatch, tmp_path) -> None:
    destination = tmp_path / "annual.csv"

    def duplicate_first_id(rows):
        rows[1]["ward_id"] = rows[0]["ward_id"]

    _rewrite_csv(ward_carbon_data.ANNUAL_CSV_PATH, destination, duplicate_first_id)
    monkeypatch.setattr(ward_carbon_data, "ANNUAL_CSV_PATH", destination)

    with pytest.raises(ValueError, match="Duplicate ward_id"):
        ward_carbon_data.load_annual_ward_carbon()
