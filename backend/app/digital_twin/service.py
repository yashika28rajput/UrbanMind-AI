import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from math import isfinite
from typing import Any

import pandas as pd

from app.schemas.environmental_data import METRIC_UNITS
from app.services import environmental_data as environmental_data_service


BASE_DIR = Path(__file__).resolve().parents[3]
DIGITAL_TWIN_DIR = Path(__file__).resolve().parent
ENVIRONMENT_FILE = BASE_DIR / "data" / "processed" / "ml" / "environmental" / "delhi_ward_environmental_risk.csv"
HEALTH_FILE = BASE_DIR / "data" / "processed" / "ml" / "health" / "delhi_ward_health_impact.csv"
SNAPSHOT_PATH = DIGITAL_TWIN_DIR / "delhi_virtual_city_model.json"

# Currentness limits are deliberately explicit because imported records have no
# automatic deletion or refresh. AQI and air-quality observations age faster
# than land-cover metrics. Green-cover and land-surface-temperature records
# remain eligible for at most one year.
OBSERVATION_MAX_AGE_DAYS = {
    "aqi": 7,
    "green_cover": 365,
    "land_surface_temperature": 365,
}
OBSERVATION_TWIN_FIELDS = {
    "aqi": ("aqi", next(iter(METRIC_UNITS["aqi"]))),
    "land_surface_temperature": ("temperature", next(iter(METRIC_UNITS["land_surface_temperature"]))),
    "green_cover": ("green_cover", next(iter(METRIC_UNITS["green_cover"]))),
}
# Only observed and official classifications may replace the snapshot. Derived,
# estimated, and illustrative rows lack a comparable authority signal to the
# existing snapshot and therefore remain visible in Data Management only.
OBSERVATION_CLASSIFICATION_PRIORITY = {"observed": 1, "official": 2}


def _safe_float(value: Any) -> float | None:
    """Return finite numeric observations while preserving missing values and zero."""
    if value is None or pd.isna(value):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if isfinite(result) else None


def _mean_metric(states: list[dict[str, Any]], metric: str, digits: int) -> float | None:
    values = [value for state in states if (value := state.get(metric)) is not None]
    return round(sum(values) / len(values), digits) if values else None


def _apply_environmental_observations(
    model: dict[str, Any], observations: list[Any], *, as_of_date: date,
) -> dict[str, Any]:
    """Overlay eligible ward observations while retaining the CSV snapshot fallback.

    Higher classification wins before recency; within a classification the
    newest observation date wins. Conflicting top-ranked values for the same
    ward/date/classification are ignored so the existing snapshot remains.
    """
    merged = deepcopy(model)
    wards = {
        int(ward["ward_no"]): ward
        for ward in merged.get("wards", [])
        if isinstance(ward, dict) and str(ward.get("ward_no", "")).isdigit()
    }
    candidates: dict[tuple[int, str], list[Any]] = {}
    for observation in observations:
        mapping = OBSERVATION_TWIN_FIELDS.get(getattr(observation, "metric", ""))
        ward_no = getattr(observation, "ward_id", None)
        observed_on = getattr(observation, "observation_date", None)
        classification = getattr(observation, "data_classification", "")
        if mapping is None or ward_no not in wards or classification not in OBSERVATION_CLASSIFICATION_PRIORITY:
            continue
        if not isinstance(observed_on, date):
            continue
        age_days = (as_of_date - observed_on).days
        if age_days < 0 or age_days > OBSERVATION_MAX_AGE_DAYS[observation.metric]:
            continue
        if getattr(observation, "unit", None) != mapping[1]:
            continue
        try:
            value = float(observation.value)
        except (TypeError, ValueError):
            continue
        if not isfinite(value):
            continue
        if observation.metric == "aqi" and not 0 <= value <= 500:
            continue
        if observation.metric == "green_cover" and not 0 <= value <= 100:
            continue
        if observation.metric == "land_surface_temperature" and not -90 <= value <= 80:
            continue
        candidates.setdefault((int(ward_no), observation.metric), []).append(observation)

    for (ward_no, metric), rows in candidates.items():
        priority = OBSERVATION_CLASSIFICATION_PRIORITY
        best_rank = max((priority[row.data_classification], row.observation_date) for row in rows)
        best = [
            row for row in rows
            if (priority[row.data_classification], row.observation_date) == best_rank
        ]
        values = {float(row.value) for row in best}
        if len(values) != 1:
            continue
        # Same-day, same-classification duplicates with the same value are
        # equivalent for calculation; choose deterministically for provenance.
        selected = max(
            best,
            key=lambda row: (
                row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                str(row.record_id),
            ),
        )
        twin_field, _unit = OBSERVATION_TWIN_FIELDS[metric]
        wards[ward_no][twin_field] = float(selected.value)
        provenance = dict(wards[ward_no].get("metric_provenance") or {})
        provenance[twin_field] = {
            "record_id": selected.record_id,
            "metric": selected.metric,
            "observation_date": selected.observation_date.isoformat(),
            "unit": selected.unit,
            "data_classification": selected.data_classification,
            "source_name": selected.source_name,
            "source_reference": selected.source_reference,
            "recorded_at": selected.created_at.isoformat() if selected.created_at else None,
        }
        wards[ward_no]["metric_provenance"] = provenance

    summary = merged.get("summary", {})
    summary["average_aqi"] = _mean_metric(list(wards.values()), "aqi", 2)
    summary["average_temperature_c"] = _mean_metric(list(wards.values()), "temperature", 2)
    summary["average_green_cover_pct"] = _mean_metric(list(wards.values()), "green_cover", 2)
    merged["summary"] = summary
    merged["wards"] = list(wards.values())
    return merged


def _extract_ward_metrics() -> list[dict[str, Any]]:
    environment = pd.read_csv(ENVIRONMENT_FILE)
    health = pd.read_csv(HEALTH_FILE)

    common_columns = ["Ward_No", "Ward_Name"]
    environment = environment.copy()
    health = health.copy()

    for frame in (environment, health):
        frame["Ward_No"] = pd.to_numeric(frame["Ward_No"], errors="coerce")
        frame["Ward_No"] = frame["Ward_No"].astype("Int64")

    merged = environment.merge(
        health[common_columns + ["TOT_P", "health_exposure_score", "population_vulnerability_index"]],
        on=["Ward_No", "Ward_Name"],
        how="left",
    )

    if merged.empty:
        raise ValueError("No digital twin ward data available.")

    states: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        ward_no = int(row["Ward_No"])
        ward_name = str(row.get("Ward_Name", f"Ward_{ward_no}"))
        aqi = _safe_float(row.get("final_AQI"))
        temperature = _safe_float(row.get("mean_LST_C"))
        vegetation_risk = _safe_float(row.get("vegetation_risk_index"))
        traffic_density = _safe_float(row.get("traffic_risk_index", row.get("traffic_pressure_index")))
        green_cover = (
            max(0.0, min(100.0, 100.0 - (vegetation_risk * 100.0)))
            if vegetation_risk is not None else None
        )
        health_exposure = _safe_float(row.get("health_exposure_score"))
        health_risk = (
            min(1.0, max(0.0, health_exposure / 100.0))
            if health_exposure is not None else None
        )
        population = _safe_float(row.get("TOT_P"))

        states.append(
            {
                "city": "Delhi",
                "zone": f"Ward_{ward_no}",
                "location": ward_name,
                "ward_no": ward_no,
                "aqi": round(aqi, 2) if aqi is not None else None,
                "temperature": round(temperature, 2) if temperature is not None else None,
                "green_cover": round(green_cover, 2) if green_cover is not None else None,
                "traffic_density": round(traffic_density, 4) if traffic_density is not None else None,
                "health_risk": round(health_risk, 4) if health_risk is not None else None,
                "population": int(population) if population is not None else None,
            }
        )

    return states


def build_virtual_city_model() -> dict[str, Any]:
    states = _extract_ward_metrics()
    if not states:
        raise ValueError("Digital twin model is empty.")

    summary = {
        "city": "Delhi",
        "phase": "PHASE 5 — Urban Digital Twin",
        "zone_count": len(states),
        "average_aqi": _mean_metric(states, "aqi", 2),
        "average_temperature_c": _mean_metric(states, "temperature", 2),
        "average_green_cover_pct": _mean_metric(states, "green_cover", 2),
        "average_traffic_density": _mean_metric(states, "traffic_density", 4),
        "average_health_risk": _mean_metric(states, "health_risk", 4),
    }

    model = {
        "city": "Delhi",
        "phase": "PHASE 5 — Urban Digital Twin",
        "digital_twin_type": "virtual_city_model",
        "summary": summary,
        "wards": states,
    }

    with SNAPSHOT_PATH.open("w", encoding="utf-8") as file:
        json.dump(model, file, indent=2)

    return model


def get_virtual_city_model() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        model = build_virtual_city_model()
    else:
        with SNAPSHOT_PATH.open("r", encoding="utf-8") as file:
            model = json.load(file)
    observations = environmental_data_service.get_digital_twin_observations(as_of_date=date.today())
    return _apply_environmental_observations(model, observations, as_of_date=date.today())


def get_ward_state(ward_no: int) -> dict[str, Any]:
    model = get_virtual_city_model()
    for ward in model["wards"]:
        if ward["ward_no"] == int(ward_no):
            return ward
    raise KeyError(f"Ward {ward_no} not found in the digital twin model.")
