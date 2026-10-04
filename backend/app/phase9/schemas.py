from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class EvidenceSource(BaseModel):
    source: str
    type: str = "document"
    url: str | None = None
    page: int | None = None
    note: str | None = None


class UrbanRequest(BaseModel):
    query: str = Field(..., min_length=1)
    city: str = "Delhi"
    zone: str = "Zone X"
    objective: str | None = None
    constraints: list[str] = Field(default_factory=list)
    requested_interventions: list[str] = Field(default_factory=list)
    scenario: str | None = None

    @field_validator("constraints", "requested_interventions")
    @classmethod
    def normalize_lists(cls, value: list[str]) -> list[str]:
        return [str(item).strip() for item in value if str(item).strip()]


class DataStatus(BaseModel):
    data_available: bool = True
    missing_datasets: list[str] = Field(default_factory=list)
    data_quality: str = "good"
    freshness: str = "current"
    coverage: str = "city-level"
    warnings: list[str] = Field(default_factory=list)


class ForecastResult(BaseModel):
    aqi_prediction: float | None = None
    uhi_prediction: float | None = None
    prediction_horizon: str = "24h"
    confidence: float | None = None
    model_name: str = "mock_urban_model"
    model_version: str = "v1.0"
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EnvironmentResult(BaseModel):
    air_quality_impact: str = "mixed"
    heat_impact: str = "moderate"
    green_cover_impact: str = "positive"
    carbon_impact: str = "moderate reduction"
    environmental_risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class HealthResult(BaseModel):
    exposure_level: str = "elevated"
    health_risk: str = "moderate"
    affected_population: int = 0
    risk_factors: list[str] = Field(default_factory=list)
    uncertainty: str = "moderate"
    evidence_ids: list[str] = Field(default_factory=list)


class EconomicResult(BaseModel):
    estimated_cost: float | None = None
    operating_cost: float | None = None
    maintenance_cost: float | None = None
    cost_assumptions: list[str] = Field(default_factory=list)
    cost_range: list[float] = Field(default_factory=list)
    uncertainty: str = "moderate"


class PolicyResult(BaseModel):
    applicable_policies: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    policy_conflicts: list[str] = Field(default_factory=list)
    jurisdiction: str = "Delhi"
    evidence_ids: list[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    candidate_interventions: list[str] = Field(default_factory=list)
    feasible_interventions: list[str] = Field(default_factory=list)
    selected_interventions: list[str] = Field(default_factory=list)
    objective_values: dict[str, float] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    rationale: str = "Generated from explicit constraints and objective weights."


class CriticResult(BaseModel):
    issues: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    constraint_violations: list[str] = Field(default_factory=list)
    model_uncertainty: list[str] = Field(default_factory=list)
    contradictory_results: list[str] = Field(default_factory=list)
    recommended_revisions: list[str] = Field(default_factory=list)
    critic_status: Literal["passed", "needs_revision"] = "passed"


class ReportResult(BaseModel):
    executive_summary: str = ""
    problem_statement: str = ""
    baseline: str = ""
    findings: list[str] = Field(default_factory=list)
    evaluated_interventions: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSource] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)


class UrbanState(BaseModel):
    workflow_id: str = "urbanmind_run_default"
    request: UrbanRequest
    data_status: DataStatus = Field(default_factory=DataStatus)
    forecasts: ForecastResult | None = None
    environmental_analysis: EnvironmentResult | None = None
    health_analysis: HealthResult | None = None
    economic_analysis: EconomicResult | None = None
    policy_analysis: PolicyResult | None = None
    candidate_interventions: list[str] = Field(default_factory=list)
    optimization_results: OptimizationResult | None = None
    critic_results: CriticResult | None = None
    revisions: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSource] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    final_report: ReportResult | None = None
    workflow_status: str = "initialized"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    current_agent: str | None = None
    completed_agents: list[str] = Field(default_factory=list)
    next_agent: str | None = None

    model_config = {"extra": "allow"}
