from __future__ import annotations

import csv
from io import BytesIO, StringIO
import json

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.environmental_data import EnvironmentalObservation
from app.database.urban_memory_store import Base
from app.config import settings
from app.main import app
from app.services import environmental_data as environmental_data_service


client = TestClient(app)

MAPPING = {
    "ward_id": "ward",
    "observation_date": "date",
    "metric": "metric",
    "value": "value",
    "unit": "unit",
    "data_classification": "classification",
    "source_name": "source",
    "source_reference": "reference",
    "notes": "notes",
}


def csv_bytes(rows: list[list[str]] | None = None) -> bytes:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(MAPPING.values())
    for row in rows or [["80", "2026-07-01", "pm25", "59.1", "µg/m³", "observed", "Station A", "sensor-7", "raw station measurement"]]:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


@pytest.fixture
def isolated_environmental_database(tmp_path, monkeypatch):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'environmental.sqlite3'}")

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    monkeypatch.setattr(environmental_data_service, "SessionLocal", factory)
    monkeypatch.setattr(environmental_data_service, "initialize_database", lambda: Base.metadata.create_all(test_engine))
    monkeypatch.setattr(environmental_data_service, "get_known_ward_ids", lambda: {1, 80})
    yield factory
    test_engine.dispose()


def _upload(file_bytes: bytes, filename: str = "observations.csv") -> dict[str, tuple[str, bytes, str]]:
    content_type = "text/csv" if filename.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return {"file": (filename, file_bytes, content_type)}


def test_csv_preview_validate_and_confirmed_import_are_provenance_preserving_and_idempotent(
    isolated_environmental_database,
) -> None:
    content = csv_bytes()
    preview = client.post("/api/v1/environmental-data/uploads/preview", files=_upload(content))

    assert preview.status_code == 200, preview.text
    preview_data = preview.json()
    assert preview_data["columns"] == list(MAPPING.values())
    assert preview_data["total_rows_read"] == 1
    assert preview_data["preview_rows"][0]["source"] == "Station A"
    assert isolated_environmental_database().query(EnvironmentalObservation).count() == 0

    form = {"mapping_json": json.dumps(MAPPING)}
    validation = client.post(
        "/api/v1/environmental-data/uploads/validate",
        files=_upload(content),
        data=form,
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["valid_rows"] == 1
    assert validation.json()["invalid_rows"] == 0
    assert validation.json()["duplicate_rows"] == 0
    assert isolated_environmental_database().query(EnvironmentalObservation).count() == 0

    imported = client.post(
        "/api/v1/environmental-data/imports/confirm",
        files=_upload(content),
        data={**form, "checksum": preview_data["checksum"]},
    )
    assert imported.status_code == 200, imported.text
    result = imported.json()
    assert result["rows_inserted"] == 1
    assert result["rows_skipped"] == 0
    assert result["import_id"]
    assert isolated_environmental_database().query(EnvironmentalObservation).count() == 1

    repeated = client.post(
        "/api/v1/environmental-data/imports/confirm",
        files=_upload(content),
        data={**form, "checksum": preview_data["checksum"]},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["idempotent_retry"] is True
    assert repeated.json()["rows_inserted"] == 0
    assert isolated_environmental_database().query(EnvironmentalObservation).count() == 1

    listed = client.get("/api/v1/environmental-data/records", params={"ward_id": 80, "metric": "pm25"})
    assert listed.status_code == 200, listed.text
    record = listed.json()["records"][0]
    assert record["value"] == 59.1
    assert record["unit"] == "µg/m³"
    assert record["data_classification"] == "observed"
    assert record["source_name"] == "Station A"
    assert record["source_reference"] == "sensor-7"


def test_valid_xlsx_import_and_formula_cells_are_handled_without_evaluation(isolated_environmental_database) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(list(MAPPING.values()))
    worksheet.append([80, "2026-07-01", "pm25", 59.1, "µg/m³", "official", "Official feed", "ref-80", None])
    output = BytesIO()
    workbook.save(output)
    content = output.getvalue()
    preview = client.post(
        "/api/v1/environmental-data/uploads/preview",
        files=_upload(content, "observations.xlsx"),
    )
    assert preview.status_code == 200, preview.text
    response = client.post(
        "/api/v1/environmental-data/imports/confirm",
        files=_upload(content, "observations.xlsx"),
        data={"mapping_json": json.dumps(MAPPING), "checksum": preview.json()["checksum"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["rows_inserted"] == 1
    assert isolated_environmental_database().query(EnvironmentalObservation).count() == 1

    formula_book = Workbook()
    formula_sheet = formula_book.active
    formula_sheet.append(list(MAPPING.values()))
    formula_sheet.append([80, "2026-07-01", "pm25", "=1+1", "µg/m³", "observed", "Station", "ref", None])
    formula_output = BytesIO()
    formula_book.save(formula_output)
    rejected = client.post(
        "/api/v1/environmental-data/uploads/preview",
        files=_upload(formula_output.getvalue(), "formula.xlsx"),
    )
    assert rejected.status_code == 422
    assert "formula" in rejected.json()["detail"].lower()


@pytest.mark.parametrize(
    ("row", "expected_reason"),
    [
        (["999", "2026-07-01", "pm25", "1", "µg/m³", "observed", "Station", "r1", ""], "Unknown ward"),
        (["80", "not-a-date", "pm25", "1", "µg/m³", "observed", "Station", "r2", ""], "ISO date"),
        (["80", "2026-07-01", "pm25", "NaN", "µg/m³", "observed", "Station", "r3", ""], "finite"),
        (["80", "2026-07-01", "pm25", "1", "ppb", "observed", "Station", "r4", ""], "not supported"),
        (["80", "2026-07-01", "pm25", "1", "µg/m³", "made-up", "Station", "r5", ""], "Input should be"),
        (["80", "2026-07-01", "population", "1.5", "people", "observed", "Station", "r6", ""], "whole number"),
    ],
)
def test_import_validation_reports_bad_rows_without_persisting(
    isolated_environmental_database,
    row: list[str],
    expected_reason: str,
) -> None:
    response = client.post(
        "/api/v1/environmental-data/uploads/validate",
        files=_upload(csv_bytes([row])),
        data={"mapping_json": json.dumps(MAPPING)},
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert report["total_rows_read"] == 1
    assert report["valid_rows"] == 0
    assert report["invalid_rows"] == 1
    assert report["errors"][0]["row_number"] == 2
    assert expected_reason.lower() in report["errors"][0]["reason"].lower()
    assert isolated_environmental_database().query(EnvironmentalObservation).count() == 0


def test_missing_mapping_duplicates_and_checksum_mismatch_are_reported(isolated_environmental_database) -> None:
    content = csv_bytes()
    missing_mapping = {key: value for key, value in MAPPING.items() if key != "unit"}
    report = client.post(
        "/api/v1/environmental-data/uploads/validate",
        files=_upload(content),
        data={"mapping_json": json.dumps(missing_mapping)},
    )
    assert report.status_code == 200
    assert any(issue["row_number"] == 2 and issue["field"] == "mapping" for issue in report.json()["errors"])

    duplicated = client.post(
        "/api/v1/environmental-data/uploads/validate",
        files=_upload(csv_bytes([
            ["80", "2026-07-01", "pm25", "59.1", "µg/m³", "observed", "Station A", "sensor-7", ""],
            ["80", "2026-07-01", "pm25", "59.1", "µg/m³", "observed", "Station A", "sensor-7", ""],
        ])),
        data={"mapping_json": json.dumps(MAPPING)},
    )
    assert duplicated.status_code == 200
    assert duplicated.json()["duplicate_rows"] == 1
    assert duplicated.json()["errors"][0]["kind"] == "duplicate"

    preview = client.post("/api/v1/environmental-data/uploads/preview", files=_upload(content))
    mismatch = client.post(
        "/api/v1/environmental-data/imports/confirm",
        files=_upload(content),
        data={"mapping_json": json.dumps(MAPPING), "checksum": "0" * 64},
    )
    assert mismatch.status_code == 422
    assert "changed after preview" in mismatch.json()["detail"]
    assert isolated_environmental_database().query(EnvironmentalObservation).count() == 0


def test_empty_malformed_unsupported_oversized_and_row_limited_uploads(monkeypatch) -> None:
    empty = client.post("/api/v1/environmental-data/uploads/preview", files=_upload(b"", "empty.csv"))
    malformed = client.post("/api/v1/environmental-data/uploads/preview", files=_upload(b"\xff\x00", "bad.csv"))
    unsupported = client.post("/api/v1/environmental-data/uploads/preview", files=_upload(b"anything", "legacy.xls"))
    assert empty.status_code == 422
    assert malformed.status_code == 422
    assert unsupported.status_code == 422
    assert "not supported" in unsupported.json()["detail"]

    monkeypatch.setattr(settings, "ENVIRONMENTAL_UPLOAD_MAX_BYTES", 10)
    oversized = client.post("/api/v1/environmental-data/uploads/preview", files=_upload(b"x" * 11))
    assert oversized.status_code == 413
    monkeypatch.setattr(settings, "ENVIRONMENTAL_UPLOAD_MAX_BYTES", 5 * 1024 * 1024)

    monkeypatch.setattr(settings, "ENVIRONMENTAL_UPLOAD_MAX_ROWS", 1)
    too_many = client.post(
        "/api/v1/environmental-data/uploads/preview",
        files=_upload(csv_bytes([
            ["80", "2026-07-01", "pm25", "1", "µg/m³", "observed", "Station", "r1", ""],
            ["80", "2026-07-02", "pm25", "2", "µg/m³", "observed", "Station", "r2", ""],
        ])),
    )
    assert too_many.status_code == 422
    assert "row limit" in too_many.json()["detail"]


def test_manual_entry_server_validation_duplicate_and_pagination(isolated_environmental_database) -> None:
    record = {
        "ward_id": 80,
        "observation_date": "2026-07-01",
        "metric": "temperature",
        "value": 31.3,
        "unit": "°C",
        "data_classification": "observed",
        "source_name": "Delhi weather feed",
        "source_reference": "station-feed-2026-07-01",
        "notes": "Hourly observation.",
    }
    created = client.post("/api/v1/environmental-data/records", json=record)
    assert created.status_code == 201, created.text
    assert created.json()["record_id"].startswith("ENV-")

    duplicate = client.post("/api/v1/environmental-data/records", json=record)
    assert duplicate.status_code == 409

    invalid = client.post("/api/v1/environmental-data/records", json={**record, "unit": "people"})
    assert invalid.status_code == 422

    unknown = client.post("/api/v1/environmental-data/records", json={**record, "ward_id": 999})
    assert unknown.status_code == 422

    page = client.get("/api/v1/environmental-data/records", params={"limit": 1, "offset": 0})
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert len(page.json()["records"]) == 1