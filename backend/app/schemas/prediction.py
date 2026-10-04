from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class AQIPredictionRequest(BaseModel):
    """Request payload for AQI prediction."""

    features: Dict[str, Any] = Field(
        ...,
        description="AQI model feature dictionary keyed by the trained model feature names.",
    )

    model_config = ConfigDict(extra="ignore")


class UrbanHeatPredictionRequest(BaseModel):
    """Request payload for urban heat prediction."""

    features: Dict[str, Any] = Field(
        ...,
        description="Urban heat model feature dictionary keyed by the trained model feature names.",
    )

    model_config = ConfigDict(extra="ignore")


class GreenCoverPredictionRequest(BaseModel):
    """Request payload for green cover estimation."""

    features: Dict[str, Any] = Field(
        ...,
        description="Land-use and vegetation features used to estimate green cover percentage.",
    )

    model_config = ConfigDict(extra="ignore")


class CarbonReductionRequest(BaseModel):
    """Request payload for carbon reduction estimation."""

    features: Dict[str, Any] = Field(
        ...,
        description="Green-cover and environmental risk features used to estimate CO2 reduction.",
    )

    model_config = ConfigDict(extra="ignore")


class HealthRiskRequest(BaseModel):
    """Request payload for health risk prediction."""

    features: Dict[str, Any] = Field(
        ...,
        description="AQI, heat, population, and exposure inputs for the health risk model.",
    )

    model_config = ConfigDict(extra="ignore")
