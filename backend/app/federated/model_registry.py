from __future__ import annotations

from .model_adapter import AQIModelAdapter

MODEL_REGISTRY: dict[str, type[AQIModelAdapter]] = {
    "aqi_model": AQIModelAdapter,
    "aqi": AQIModelAdapter,
    "urban_heat_model": AQIModelAdapter,
    "green_cover_model": AQIModelAdapter,
    "carbon_model": AQIModelAdapter,
    "health_risk_model": AQIModelAdapter,
}


def get_model_adapter(model_name: str) -> type[AQIModelAdapter]:
    normalized_name = model_name.lower().replace("-", "_")
    registry_key = normalized_name if normalized_name in MODEL_REGISTRY else "aqi_model"
    return MODEL_REGISTRY[registry_key]


__all__ = ["MODEL_REGISTRY", "get_model_adapter"]
