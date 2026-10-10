import json
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from app.schemas.prediction import (
    AQIPredictionRequest,
    CarbonReductionRequest,
    GreenCoverPredictionRequest,
    HealthRiskRequest,
    UrbanHeatPredictionRequest,
)
from app.services.prediction_service import (
    estimate_carbon_reduction,
    predict_aqi,
    predict_green_cover,
    predict_health_risk,
    predict_urban_heat,
)

router = APIRouter(prefix="/api/v1", tags=["prediction-layer"])


def _metadata_version(model_name: str) -> str:
    metadata_map = {
        "aqi": "models/aqi/aqi_model_info.json",
        "uhi": "models/urban_heat/urban_heat_model_info.json",
        "green_cover": "models/green_cover_model_info.json",
        "carbon": "models/carbon_model_info.json",
        "health_risk": "models/health_risk_model_info.json",
    }
    info_path = Path(__file__).resolve().parents[3] / metadata_map[model_name]
    if not info_path.exists():
        return "unknown"
    with info_path.open("r", encoding="utf-8") as handle:
        info = json.load(handle)
    return str(info.get("version") or info.get("selected_model") or info.get("model_name") or info.get("model") or "unknown")


# What kind of evidence stands behind each output. "trained_ml" means a fitted model artifact;
# "rule_based_estimate" means a hand-written formula with fixed coefficients and NO training
# data or validation behind it. Do not present the latter as a measured or learned prediction.
_EVIDENCE_TYPE = {
    "aqi": ("trained_ml", "Fitted on same-time pollutant readings that define the AQI target; reported accuracy "
            "is not evidence of forecasting skill (see docs/AUDIT.md)."),
    "uhi": ("trained_ml", "Single-city dataset (about 270 wards); small sample, spatial validation not performed."),
    "green_cover": ("rule_based_estimate", "Fixed-coefficient formula on land-use shares; not validated against ground truth."),
    "carbon": ("rule_based_estimate", "Fixed-coefficient formula; not a validated carbon model. Use POST /api/v1/carbon/calculate "
               "with sourced emission factors for traceable accounting."),
    "health_risk": ("rule_based_estimate", "Fixed-weight composite score; not an epidemiological model."),
}


def _wrap_prediction_response(model_name: str, result: dict[str, Any]) -> dict[str, Any]:
    prediction_value = result.get("predicted_value")
    evidence_type, limitation = _EVIDENCE_TYPE.get(model_name, ("unknown", "No provenance information."))
    return {
        "evidence_type": evidence_type,
        "limitations": limitation,
        "prediction": prediction_value,
        "model": result.get("model_name", model_name),
        "model_version": _metadata_version(model_name),
        "status": "success",
        "target": result.get("target"),
        "details": result,
    }


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "project": "UrbanMind AI",
        "phase": "PHASE 4 — AI Prediction Layer",
    }


@router.get("/models")
async def list_available_models() -> dict[str, list[dict[str, str]]]:
    return {
        "models": [
            {
                "name": "aqi",
                "description": "Predict AQI using trained pollution and time-based features.",
            },
            {
                "name": "urban_heat",
                "description": "Predict urban heat intensity from land, population and infrastructure indicators.",
            },
            {
                "name": "green_cover",
                "description": "Estimate green cover share from vegetation and land-use ratios.",
            },
            {
                "name": "carbon_reduction",
                "description": "Estimate expected CO2 reduction from intervention and green cover expansion.",
            },
            {
                "name": "health_risk",
                "description": "Estimate health risk based on AQI, heat exposure, and population vulnerability.",
            },
        ]
    }


@router.post("/predict/aqi")
async def predict_aqi_endpoint(request: AQIPredictionRequest) -> dict[str, object]:
    try:
        return predict_aqi(request.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aqi/predict")
async def predict_aqi_phase14_endpoint(request: AQIPredictionRequest) -> dict[str, object]:
    try:
        return _wrap_prediction_response("aqi", predict_aqi(request.features))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/predict/urban-heat")
async def predict_urban_heat_endpoint(request: UrbanHeatPredictionRequest) -> dict[str, object]:
    try:
        return predict_urban_heat(request.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/uhi/predict")
async def predict_uhi_phase14_endpoint(request: UrbanHeatPredictionRequest) -> dict[str, object]:
    try:
        return _wrap_prediction_response("uhi", predict_urban_heat(request.features))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/predict/green-cover")
async def predict_green_cover_endpoint(request: GreenCoverPredictionRequest) -> dict[str, object]:
    try:
        return predict_green_cover(request.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/green-cover/predict")
async def predict_green_cover_phase14_endpoint(request: GreenCoverPredictionRequest) -> dict[str, object]:
    try:
        return _wrap_prediction_response("green_cover", predict_green_cover(request.features))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/predict/carbon-reduction")
async def estimate_carbon_reduction_endpoint(request: CarbonReductionRequest) -> dict[str, object]:
    try:
        return estimate_carbon_reduction(request.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/carbon/predict")
async def estimate_carbon_phase14_endpoint(request: CarbonReductionRequest) -> dict[str, object]:
    try:
        return _wrap_prediction_response("carbon", estimate_carbon_reduction(request.features))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/predict/health-risk")
async def predict_health_risk_endpoint(request: HealthRiskRequest) -> dict[str, object]:
    try:
        return predict_health_risk(request.features)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/health-risk/predict")
async def predict_health_risk_phase14_endpoint(request: HealthRiskRequest) -> dict[str, object]:
    try:
        return _wrap_prediction_response("health_risk", predict_health_risk(request.features))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
