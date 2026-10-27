from __future__ import annotations

import json
from copy import deepcopy
from math import isfinite
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.digital_twin.service import get_virtual_city_model, get_ward_state
from app.services.prediction_service import CARBON_REDUCTION_UNAVAILABLE_REASON

router = APIRouter(prefix="/api/v1/digital-twin", tags=["digital-twin"])
PROJECT_DIR = Path(__file__).resolve().parents[3]
WARD_GEOJSON_PATH = (
    PROJECT_DIR / "data" / "processed" / "ml" / "environmental" / "delhi_ward_environmental_risk.geojson"
)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _finite_difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    difference = left - right
    return difference if isfinite(difference) else None


@router.get("/summary")
async def digital_twin_summary() -> dict[str, object]:
    model = get_virtual_city_model()
    summary = {
        **model["summary"],
        "carbon_reduction_availability_reason": CARBON_REDUCTION_UNAVAILABLE_REASON,
    }
    return {
        "city": model["city"],
        "phase": model["phase"],
        "summary": summary,
    }


@router.get("/wards")
async def digital_twin_wards() -> dict[str, object]:
    model = get_virtual_city_model()
    return {
        "city": model["city"],
        "phase": model["phase"],
        "wards": model["wards"],
    }


@router.get("/wards/geojson")
async def digital_twin_ward_geojson() -> dict[str, Any]:
    try:
        with WARD_GEOJSON_PATH.open("r", encoding="utf-8") as source:
            feature_collection = json.load(source)
        model = get_virtual_city_model()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Ward boundary data is unavailable.") from exc

    metrics = {ward["ward_no"]: ward for ward in model["wards"]}
    features = feature_collection.get("features")
    if not isinstance(features, list):
        raise HTTPException(status_code=503, detail="Ward boundary data is invalid.")
    for feature in features:
        properties = feature.get("properties", {})
        try:
            ward_number = int(properties["Ward_No"])
        except (KeyError, TypeError, ValueError):
            continue
        properties.update(metrics.get(ward_number, {}))
        feature["properties"] = properties
    feature_collection["features"] = features
    return feature_collection


@router.get("/ward/{ward_no}")
async def digital_twin_ward(ward_no: int) -> dict[str, object]:
    try:
        return get_ward_state(ward_no)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/state")
async def digital_twin_state(request: dict[str, Any] | None = None) -> dict[str, Any]:
    model = get_virtual_city_model()
    payload = request or {}
    ward_no = payload.get("ward_no")
    if ward_no is not None:
        try:
            baseline = get_ward_state(int(ward_no))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "baseline_state": baseline,
            "scenario_id": payload.get("scenario_id", f"dt-scenario-{ward_no}"),
            "model_version": model.get("phase", "v1"),
            "status": "success",
        }
    return {
        "baseline_state": model["summary"],
        "scenario_id": payload.get("scenario_id", "digital-twin-baseline"),
        "model_version": model.get("phase", "v1"),
        "status": "success",
    }


@router.post("/simulate")
async def digital_twin_simulate(request: dict[str, Any] | None = None) -> dict[str, Any]:
    model = get_virtual_city_model()
    payload = request or {}
    baseline = deepcopy(payload.get("baseline_state") or model["summary"])
    metric_names = {"aqi", "temperature", "green_cover", "traffic_density", "health_risk", "population"}
    for metric in metric_names & baseline.keys():
        baseline[metric] = _finite_number(baseline[metric])
    simulated = deepcopy(baseline)
    adjustments = payload.get("adjustments") or {}
    for key, value in adjustments.items():
        if key in simulated:
            current_value = _finite_number(simulated[key])
            adjustment = _finite_number(value)
            if current_value is None or adjustment is None:
                continue
            result = current_value + adjustment
            if isfinite(result):
                simulated[key] = result
    metric_changes = {
        metric: {
            "baseline": baseline.get(metric),
            "simulated": simulated.get(metric),
            "delta": _finite_difference(simulated.get(metric), baseline.get(metric)),
        }
        for metric in sorted(set(baseline) | set(simulated))
        if metric in metric_names
    }
    return {
        "baseline_state": baseline,
        "simulated_state": simulated,
        "metric_changes": metric_changes,
        "scenario_id": payload.get("scenario_id", "digital-twin-simulated"),
        "model": model.get("digital_twin_type", "virtual_city_model"),
        "model_version": model.get("phase", "v1"),
        "status": "success",
    }


@router.get("/state/{state_id}")
async def digital_twin_state_by_id(state_id: str) -> dict[str, Any]:
    if state_id.isdigit():
        try:
            return {"state": get_ward_state(int(state_id)), "status": "success"}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    model = get_virtual_city_model()
    return {"state": model["summary"], "status": "success"}
