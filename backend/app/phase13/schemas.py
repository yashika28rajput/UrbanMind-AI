from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.phase11.schemas import SimulationResult
from app.phase12.schemas import OptimizationResult

ModelName = Literal["aqi", "urban_heat", "green_cover", "carbon", "carbon_reduction", "health_risk"]


class ExplanationRequest(BaseModel):
    model_name: ModelName
    features: dict[str, float]
    background_features: list[dict[str, float]] = Field(default_factory=list)


class FeatureContribution(BaseModel):
    feature: str
    feature_value: float | None = None
    shap_value: float | None = None
    influence: Literal["raises_prediction", "lowers_prediction", "neutral", "unknown"]
    attribution_method: str = "SHAP"


class ExplanationResult(BaseModel):
    model_name: str
    model_version: str
    prediction: float | None
    target: str
    unit: str | None = None
    baseline_value: float | None = None
    feature_contributions: list[FeatureContribution] = Field(default_factory=list)
    confidence: float | None = None
    uncertainty: dict[str, float | str] = Field(default_factory=dict)
    explanation_method: str


class CounterfactualRequest(BaseModel):
    model_name: ModelName
    features: dict[str, float]
    feature_name: str = Field(min_length=1)
    counterfactual_value: float


class CounterfactualResult(BaseModel):
    model_name: str
    model_version: str
    feature_name: str
    baseline_feature_value: float
    counterfactual_feature_value: float
    baseline_prediction: float
    counterfactual_prediction: float
    absolute_delta: float
    target: str


class RecommendationExplanationRequest(BaseModel):
    simulations: list[SimulationResult] = Field(min_length=1)
    optimization_result: OptimizationResult


class StrategyExplanation(BaseModel):
    scenario_id: str
    simulation_id: str
    reasons: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)


class RecommendationExplanationResult(BaseModel):
    optimization_id: str
    pareto_scenario_ids: list[str]
    preferred_scenario_id: str | None = None
    preferred_simulation_id: str | None = None
    reasons: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    strategy_explanations: list[StrategyExplanation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
