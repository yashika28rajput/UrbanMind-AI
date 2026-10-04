import json
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]
MODELS_DIR = BASE_DIR / "models"

AQI_MODEL_PATH = MODELS_DIR / "aqi" / "aqi_model.pkl"
AQI_MODEL_INFO_PATH = MODELS_DIR / "aqi" / "aqi_model_info.json"

URBAN_HEAT_MODEL_PATH = MODELS_DIR / "urban_heat" / "urban_heat_model.pkl"
URBAN_HEAT_MODEL_INFO_PATH = MODELS_DIR / "urban_heat" / "urban_heat_model_info.json"

GREEN_COVER_MODEL_PATH = MODELS_DIR / "green_cover_model.pkl"
GREEN_COVER_MODEL_INFO_PATH = MODELS_DIR / "green_cover_model_info.json"

CARBON_REDUCTION_MODEL_PATH = MODELS_DIR / "carbon_model.pkl"
CARBON_REDUCTION_MODEL_INFO_PATH = MODELS_DIR / "carbon_model_info.json"

HEALTH_RISK_MODEL_PATH = MODELS_DIR / "health_risk_model.pkl"
HEALTH_RISK_MODEL_INFO_PATH = MODELS_DIR / "health_risk_model_info.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _coerce_feature_values(
    required_features: list[str],
    raw_features: Mapping[str, Any],
    *,
    require_all: bool = True,
) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    missing = [feature for feature in required_features if feature not in raw_features]
    if missing and require_all:
        raise ValueError(f"Missing required features: {missing}")

    for feature in required_features:
        if feature not in raw_features:
            continue
        try:
            cleaned[feature] = float(raw_features[feature])
        except (TypeError, ValueError):
            raise ValueError(f"Feature '{feature}' must be numeric.") from None

    if not require_all and not cleaned:
        raise ValueError("No valid features were provided for the model.")

    return cleaned


def _aqi_category(aqi_value: float) -> str:
    if aqi_value <= 50:
        return "Good"
    if aqi_value <= 100:
        return "Satisfactory"
    if aqi_value <= 200:
        return "Moderate"
    if aqi_value <= 300:
        return "Poor"
    if aqi_value <= 400:
        return "Very Poor"
    return "Severe"


def _green_cover_category(coverage_percent: float) -> str:
    if coverage_percent < 10:
        return "Critical"
    if coverage_percent < 20:
        return "Low"
    if coverage_percent < 35:
        return "Moderate"
    if coverage_percent < 50:
        return "Healthy"
    return "Excellent"


def _risk_category(score: float) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Moderate"
    if score < 75:
        return "High"
    return "Very High"


def _green_cover_prediction_from_dict(feature_values: Mapping[str, float]) -> float:
    vegetation_columns = [
        "trees",
        "grass",
        "flooded_vegetation",
        "crops",
        "shrub_and_scrub",
        "vegetation",
    ]
    vegetation_total = sum(float(feature_values.get(column, 0.0)) for column in vegetation_columns)
    built_share = float(feature_values.get("built", 0.0))
    prediction = vegetation_total * 100.0 * (1.0 - 0.45 * built_share)
    return max(0.0, min(100.0, prediction))


def _carbon_reduction_prediction_from_dict(feature_values: Mapping[str, float]) -> float:
    green_cover_pct = float(feature_values.get("green_cover_percent", _green_cover_prediction_from_dict(feature_values)))
    emission_pressure = float(feature_values.get("emission_pressure_index", 0.0))
    intervention_strength = float(
        feature_values.get("intervention_strength", feature_values.get("urban_intervention_potential", 0.5))
    )
    prediction = (green_cover_pct / 100.0) * 170.0 + emission_pressure * 150.0 * intervention_strength
    return max(0.0, prediction)


def _health_risk_prediction_from_dict(feature_values: Mapping[str, float]) -> float:
    aqi_risk = float(feature_values.get("AQI_risk_index", float(feature_values.get("aqi", 0.0)) / 300.0))
    heat_risk = float(feature_values.get("heat_risk_index", float(feature_values.get("temperature_c", 0.0)) / 45.0))
    vulnerability = float(
        feature_values.get("population_vulnerability_index", float(feature_values.get("population_density", 0.0)) / 100000.0)
    )
    exposure = float(feature_values.get("health_exposure_score", float(feature_values.get("population_exposure", 0.0)) / 1000.0))
    score = (0.35 * aqi_risk + 0.30 * heat_risk + 0.20 * vulnerability + 0.15 * (exposure / 100.0)) * 100.0
    return max(0.0, min(100.0, score))


def predict_aqi(features: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _load_json(AQI_MODEL_INFO_PATH)
    required_features = metadata.get("features") or []
    if not required_features:
        raise ValueError("AQI model metadata does not include a feature list.")

    feature_values = _coerce_feature_values(required_features, features)
    model = joblib.load(AQI_MODEL_PATH)

    frame = pd.DataFrame([feature_values], columns=required_features)
    prediction = float(model.predict(frame)[0])

    return {
        "model_name": metadata.get("model", "Gradient Boosting"),
        "target": metadata.get("target", "AQI"),
        "predicted_value": round(prediction, 2),
        "aqi_category": _aqi_category(prediction),
        "features_used": len(required_features),
    }


def predict_urban_heat(features: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _load_json(URBAN_HEAT_MODEL_INFO_PATH)
    required_features = metadata.get("features") or []
    if not required_features:
        raise ValueError("Urban heat model metadata does not include a feature list.")

    feature_values = _coerce_feature_values(required_features, features)
    model = joblib.load(URBAN_HEAT_MODEL_PATH)

    frame = pd.DataFrame([feature_values], columns=required_features)
    prediction = float(model.predict(frame)[0])

    return {
        "model_name": metadata.get("selected_model", "Gradient Boosting"),
        "target": metadata.get("target", "mean_LST_C"),
        "predicted_value": round(prediction, 2),
        "unit": "°C",
        "features_used": len(required_features),
    }


def predict_green_cover(features: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _load_json(GREEN_COVER_MODEL_INFO_PATH)
    required_features = metadata.get("features") or []
    if not required_features:
        raise ValueError("Green cover model metadata does not include a feature list.")

    feature_values = _coerce_feature_values(required_features, features)
    model = joblib.load(GREEN_COVER_MODEL_PATH)

    if isinstance(model, dict):
        prediction = _green_cover_prediction_from_dict(feature_values)
    elif hasattr(model, "predict"):
        frame = pd.DataFrame([feature_values], columns=required_features)
        prediction = float(model.predict(frame)[0])
    else:
        raise TypeError("Unsupported green cover model type.")

    green_cover_percent = max(0.0, min(100.0, prediction))

    return {
        "model_name": metadata.get("model_name", "Green Cover Estimator"),
        "target": metadata.get("target", "green_cover_percent"),
        "predicted_value": round(green_cover_percent, 2),
        "unit": "%",
        "coverage_category": _green_cover_category(green_cover_percent),
        "features_used": len(required_features),
    }


def estimate_carbon_reduction(features: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _load_json(CARBON_REDUCTION_MODEL_INFO_PATH)
    required_features = metadata.get("features") or []
    if not required_features:
        raise ValueError("Carbon reduction model metadata does not include a feature list.")

    feature_values = _coerce_feature_values(required_features, features, require_all=False)
    model = joblib.load(CARBON_REDUCTION_MODEL_PATH)

    if isinstance(model, dict):
        prediction = _carbon_reduction_prediction_from_dict(feature_values)
    elif hasattr(model, "predict"):
        frame = pd.DataFrame([feature_values], columns=required_features)
        prediction = float(model.predict(frame)[0])
    else:
        raise TypeError("Unsupported carbon reduction model type.")

    reduction = max(0.0, prediction)

    return {
        "model_name": metadata.get("model_name", "Carbon Reduction Estimator"),
        "target": metadata.get("target", "CO2_reduction_tons"),
        "predicted_value": round(reduction, 2),
        "unit": "tCO2e/year",
        "features_used": len(required_features),
    }


def predict_health_risk(features: Mapping[str, Any]) -> dict[str, Any]:
    metadata = _load_json(HEALTH_RISK_MODEL_INFO_PATH)
    required_features = metadata.get("features") or []
    if not required_features:
        raise ValueError("Health risk model metadata does not include a feature list.")

    feature_values = _coerce_feature_values(required_features, features, require_all=False)
    model = joblib.load(HEALTH_RISK_MODEL_PATH)

    if isinstance(model, dict):
        prediction = _health_risk_prediction_from_dict(feature_values)
    elif hasattr(model, "predict"):
        frame = pd.DataFrame([feature_values], columns=required_features)
        prediction = float(model.predict(frame)[0])
    else:
        raise TypeError("Unsupported health risk model type.")

    score = max(0.0, min(100.0, prediction))

    return {
        "model_name": metadata.get("model_name", "Health Risk Estimator"),
        "target": metadata.get("target", "health_risk_score"),
        "predicted_value": round(score, 2),
        "unit": "%",
        "risk_category": _risk_category(score),
        "features_used": len(required_features),
    }
