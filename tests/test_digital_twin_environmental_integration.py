from __future__ import annotations

from datetime import date, timedelta
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.urban_memory_store import Base
from app.digital_twin import service as digital_twin_service
from app.phase10.schemas import Scenario
from app.phase11.engine import run_simulation
from app.phase11.schemas import SimulationRequest
from app.phase9.graph.state import UrbanState
from app.schemas.environmental_data import METRIC_UNITS
from app.services import environmental_data as environmental_data_service
from app.schemas.environmental_data import EnvironmentalRecordInput


def _base_model() -> dict:
    return {
        "city": "Delhi",
        "phase": "PHASE 5 — Urban Digital Twin",
        "digital_twin_type": "virtual_city_model",
        "summary": {
            "city": "Delhi",
            "phase": "PHASE 5 — Urban Digital Twin",
            "zone_count": 1,
            "average_aqi": 90.0,
            "average_temperature_c": 34.0,
            "average_green_cover_pct": 20.0,
        },
        "wards": [{
            "city": "Delhi", "zone": "Ward_80", "location": "CHANDNI CHOWK", "ward_no": 80,
            "aqi": 90.0, "temperature": 34.0, "green_cover": 20.0,
        }],
    }


def _setup_integration(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'environmental-twin.sqlite3'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(environmental_data_service, "SessionLocal", factory)
    monkeypatch.setattr(environmental_data_service, "initialize_database", lambda: Base.metadata.create_all(engine))
    monkeypatch.setattr(environmental_data_service, "get_known_ward_ids", lambda: {80})
    snapshot = tmp_path / "digital-twin.json"
    snapshot.write_text(json.dumps(_base_model()), encoding="utf-8")
    monkeypatch.setattr(digital_twin_service, "SNAPSHOT_PATH", snapshot)
    return engine


def _save(ward_id: int, metric: str, value: float, unit: str, classification: str, observed_on: date):
    return environmental_data_service.create_environmental_record(EnvironmentalRecordInput(
        ward_id=ward_id,
        observation_date=observed_on,
        metric=metric,
        value=value,
        unit=unit,
        data_classification=classification,
        source_name="Integration test source",
        source_reference=f"{metric}-{observed_on.isoformat()}-{classification}",
    ))


def _unit(metric: str) -> str:
    return next(iter(METRIC_UNITS[metric]))


def test_saved_observations_reach_twin_and_supported_phase11_baselines(monkeypatch, tmp_path) -> None:
    engine = _setup_integration(monkeypatch, tmp_path)
    try:
        today = date.today()
        aqi_record = _save(80, "aqi", 0, "AQI", "official", today)
        lst_record = _save(80, "land_surface_temperature", 29.5, _unit("land_surface_temperature"), "observed", today)
        green_record = _save(80, "green_cover", 22.0, _unit("green_cover"), "observed", today)
        # Air temperature is not interchangeable with the Twin's LST field.
        _save(80, "temperature", 41.0, _unit("temperature"), "official", today)

        ward = digital_twin_service.get_ward_state(80)
        assert ward["aqi"] == 0
        assert ward["temperature"] == 29.5
        assert ward["green_cover"] == 22
        assert ward["metric_provenance"]["aqi"]["record_id"] == aqi_record.record_id
        assert ward["metric_provenance"]["aqi"]["observation_date"] == today.isoformat()
        assert ward["metric_provenance"]["aqi"]["recorded_at"] == aqi_record.created_at.isoformat()
        assert ward["metric_provenance"]["temperature"]["record_id"] == lst_record.record_id
        assert ward["metric_provenance"]["green_cover"]["record_id"] == green_record.record_id

        scenario = Scenario(
            scenario_id="environmental-observation-bau",
            name="Business as Usual",
            description="No intervention.",
            city="Delhi",
            zone="Ward_80",
            intervention_type="baseline",
        )
        result = run_simulation(SimulationRequest(
            urban_state=UrbanState(
                workflow_id="environmental-observation-test",
                request={"query": "Baseline", "city": "Delhi", "zone": "Ward_80"},
            ),
            scenario=scenario,
        ))
        assert result.metrics["aqi"].baseline_value == 0
        assert "environmental observation" in result.metrics["aqi"].source_model
        assert aqi_record.record_id in result.metrics["aqi"].source_model
        assert result.metrics["temperature"].baseline_value == 29.5
        assert "environmental observation" in result.metrics["temperature"].source_model
        assert result.metrics["green_cover"].baseline_value == 22
        assert result.metrics["carbon_impact"].simulated_value is None
        assert result.metrics["carbon_impact"].availability_reason
        assert result.metrics["carbon_emissions"].baseline_value is None
        assert result.metrics["carbon_emissions"].simulated_value is None
        assert result.metrics["carbon_emissions"].availability_reason
    finally:
        engine.dispose()


def test_stale_conflicting_and_invalid_records_keep_csv_fallback(monkeypatch, tmp_path) -> None:
    engine = _setup_integration(monkeypatch, tmp_path)
    try:
        from types import SimpleNamespace

        today = date.today()
        stale = SimpleNamespace(
            ward_id=80, metric="aqi", value=10, unit="AQI", data_classification="official",
            observation_date=today - timedelta(days=8), record_id="stale", source_name="old",
            source_reference="old-ref", created_at=None,
        )
        bad_unit = SimpleNamespace(
            ward_id=80, metric="green_cover", value=80, unit="people", data_classification="official",
            observation_date=today, record_id="bad-unit", source_name="bad", source_reference=None, created_at=None,
        )
        air_temp = SimpleNamespace(
            ward_id=80, metric="temperature", value=10, unit=_unit("temperature"), data_classification="official",
            observation_date=today, record_id="air-temp", source_name="air", source_reference=None, created_at=None,
        )
        conflict_a = SimpleNamespace(
            ward_id=80, metric="aqi", value=50, unit="AQI", data_classification="observed",
            observation_date=today, record_id="conflict-a", source_name="a", source_reference="a", created_at=None,
        )
        conflict_b = SimpleNamespace(
            ward_id=80, metric="aqi", value=60, unit="AQI", data_classification="observed",
            observation_date=today, record_id="conflict-b", source_name="b", source_reference="b", created_at=None,
        )
        invalid = SimpleNamespace(
            ward_id=80, metric="green_cover", value=float("nan"), unit="%", data_classification="official",
            observation_date=today, record_id="invalid", source_name="bad", source_reference=None, created_at=None,
        )

        # A fresh official observation has higher authority than a conflicting
        # observed pair; the lower class does not overwrite it.
        authoritative = _save(80, "aqi", 40, "AQI", "official", today)
        protected = digital_twin_service._apply_environmental_observations(
            _base_model(),
            [authoritative, conflict_a, conflict_b],
            as_of_date=today,
        )["wards"][0]
        assert protected["aqi"] == 40
        assert protected["metric_provenance"]["aqi"]["record_id"] == authoritative.record_id

        # Stale, conflicting, incompatible-unit, unsupported air-temperature,
        # and non-finite records leave the original snapshot metrics untouched.
        ward = digital_twin_service._apply_environmental_observations(
            _base_model(), [stale, bad_unit, air_temp, conflict_a, conflict_b, invalid], as_of_date=today,
        )["wards"][0]
        assert ward["aqi"] == 90
        assert "metric_provenance" not in ward
        assert ward["temperature"] == 34.0
        assert ward["green_cover"] == 20.0
    finally:
        engine.dispose()


def test_existing_snapshot_remains_fallback_without_saved_observations(monkeypatch, tmp_path) -> None:
    engine = _setup_integration(monkeypatch, tmp_path)
    try:
        model = digital_twin_service.get_virtual_city_model()
        assert model["wards"][0]["aqi"] == 90
        assert model["wards"][0]["temperature"] == 34
        assert model["wards"][0]["green_cover"] == 20
        assert "metric_provenance" not in model["wards"][0]
        assert model["summary"]["average_aqi"] == 90
    finally:
        engine.dispose()
