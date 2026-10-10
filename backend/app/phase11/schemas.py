from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.phase10.schemas import Scenario
from app.phase9.graph.state import UrbanState


class SimulationInput(BaseModel):
    baseline_metrics: dict[str, float] = Field(default_factory=dict)
    baseline_sources: dict[str, str] = Field(default_factory=dict)
    model_features: dict[str, dict[str, float]] = Field(default_factory=dict)
    scenario_model_features: dict[str, dict[str, float]] = Field(default_factory=dict)
    scenario_features_by_id: dict[str, dict[str, dict[str, float]]] = Field(default_factory=dict)
    scenario_features_by_intervention: dict[str, dict[str, dict[str, float]]] = Field(default_factory=dict)
    scenario_estimates: dict[str, "ScenarioMetricEstimate"] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_execution_time_estimate(self) -> "SimulationInput":
        estimate = self.scenario_estimates.get("execution_time")
        if estimate is not None and (estimate.value <= 0 or estimate.unit != "years"):
            raise ValueError("execution_time requires a positive finite value in years.")
        return self


class ScenarioMetricEstimate(BaseModel):
    value: float = Field(allow_inf_nan=False)
    unit: str
    source_type: Literal["validated_model", "external_simulator", "user_input", "configured_assumption"]
    source: str = Field(min_length=1)
    model_name: str | None = None
    model_version: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    uncertainty: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_execution_time(self) -> "ScenarioMetricEstimate":
        if self.source_type == "user_input" and self.unit == "years" and self.value <= 0:
            raise ValueError("Execution-time estimates must be greater than zero years.")
        return self


class SimulatedUrbanState(BaseModel):
    city: str
    zone: str | None = None
    aqi: float | None = None
    temperature: float | None = None
    green_cover: float | None = None
    carbon_impact: float | None = None
    carbon_emissions: float | None = None
    health_risk: float | None = None
    health_benefit: float | None = None
    cost: float | None = None
    population_exposure: float | None = None
    execution_time: float | None = None
    sustainability: float | None = None


class MetricDelta(BaseModel):
    baseline_value: float | None
    simulated_value: float | None
    absolute_delta: float | None
    percentage_delta: float | None
    unit: str
    source_model: str
    confidence: float | None = None
    uncertainty: float | None = None
    availability: str = "available"
    availability_reason: str | None = None


class SimulationUncertainty(BaseModel):
    metric: str
    method: str
    value: float | None = None
    unit: str | None = None
    note: str | None = None


class SimulationMetadata(BaseModel):
    model_versions: dict[str, str] = Field(default_factory=dict)
    engine_version: str = "phase11-v1"
    reproducibility_key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float | None = Field(default=None, ge=0)
    assumptions: list[str] = Field(default_factory=list)


class SimulationRequest(BaseModel):
    urban_state: UrbanState
    scenario: Scenario
    simulation_input: SimulationInput = Field(default_factory=SimulationInput)


class SimulationResult(BaseModel):
    simulation_id: str = Field(default_factory=lambda: f"SIM-{uuid4().hex[:12].upper()}")
    scenario_id: str
    scenario_version: int
    workflow_id: str
    status: str
    baseline_state: SimulatedUrbanState
    simulated_state: SimulatedUrbanState
    metrics: dict[str, MetricDelta]
    uncertainty: list[SimulationUncertainty] = Field(default_factory=list)
    metadata: SimulationMetadata
