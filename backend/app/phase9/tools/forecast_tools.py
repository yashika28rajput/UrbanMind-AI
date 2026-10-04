from __future__ import annotations

from app.phase9.schemas import ForecastResult


def predict_aqi(city: str, zone: str) -> ForecastResult:
    baseline = 160.0 if city.lower() == "delhi" else 95.0
    return ForecastResult(
        aqi_prediction=round(baseline * 1.08, 2),
        uhi_prediction=round(2.7, 2),
        prediction_horizon="24h",
        confidence=0.78,
        model_name="mock_aqi_model",
        model_version="v1.0",
        assumptions=[f"AQI estimate based on baseline conditions for {city} {zone}."],
        warnings=[],
    )


def predict_uhi(city: str, zone: str) -> float:
    return 32.4 if city.lower() == "delhi" else 28.1
