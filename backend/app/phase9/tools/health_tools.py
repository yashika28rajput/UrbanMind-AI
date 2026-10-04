from __future__ import annotations

from app.phase9.schemas import HealthResult


def predict_health_risk(city: str, zone: str, aqi_prediction: float | None) -> HealthResult:
    base_population = 450000 if city.lower() == "delhi" else 180000
    return HealthResult(
        exposure_level="elevated",
        health_risk="moderate",
        affected_population=int(base_population * (0.25 if aqi_prediction and aqi_prediction > 150 else 0.15)),
        risk_factors=["PM2.5", "heat stress", "elderly vulnerability"],
        uncertainty="moderate",
        evidence_ids=["health-evidence-01"],
    )
