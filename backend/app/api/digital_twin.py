from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.digital_twin.service import get_virtual_city_model, get_ward_state

router = APIRouter(prefix="/api/v1/digital-twin", tags=["digital-twin"])
PROJECT_DIR = Path(__file__).resolve().parents[3]
WARD_GEOJSON_PATH = (
    PROJECT_DIR / "data" / "processed" / "ml" / "environmental" / "delhi_ward_environmental_risk.geojson"
)


@router.get("/summary")
async def digital_twin_summary() -> dict[str, object]:
    model = get_virtual_city_model()
    return {
        "city": model["city"],
        "phase": model["phase"],
        "summary": model["summary"],
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
    baseline = payload.get("baseline_state") or model["summary"]
    simulated = deepcopy(baseline)
    adjustments = payload.get("adjustments") or {}
    for key, value in adjustments.items():
        if isinstance(value, (int, float)) and key in simulated:
            simulated[key] = float(simulated.get(key, 0.0)) + float(value)
    metric_changes = {
        metric: {
            "baseline": baseline.get(metric),
            "simulated": simulated.get(metric),
            "delta": (simulated.get(metric) - baseline.get(metric)) if baseline.get(metric) is not None else None,
        }
        for metric in sorted(set(baseline) | set(simulated))
        if metric in {"aqi", "temperature", "green_cover", "traffic_density", "health_risk", "population"}
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
