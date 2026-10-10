from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from app.phase9.graph.state import UrbanState


class EstimateProvenance(BaseModel):
    source_type: Literal["validated_model", "simulation", "evidence", "configured_assumption", "user_input"]
    source_id: str = Field(min_length=1)
    model_name: str | None = None
    model_version: str | None = None


class CostEstimate(BaseModel):
    capital_cost: float | None = Field(default=None, ge=0)
    operating_cost: float | None = Field(default=None, ge=0)
    maintenance_cost: float | None = Field(default=None, ge=0)
    total_estimated_cost: float | None = Field(default=None, ge=0)
    min_cost: float | None = Field(default=None, ge=0)
    max_cost: float | None = Field(default=None, ge=0)
    currency: str = "INR"
    time_period: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    provenance: list[EstimateProvenance] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_range(self) -> CostEstimate:
        if self.min_cost is not None and self.max_cost is not None and self.min_cost > self.max_cost:
            raise ValueError("min_cost must not exceed max_cost")
        amounts = (
            self.capital_cost,
            self.operating_cost,
            self.maintenance_cost,
            self.total_estimated_cost,
            self.min_cost,
            self.max_cost,
        )
        if any(amount is not None for amount in amounts) and not self.provenance:
            raise ValueError("Numerical cost estimates require provenance.")
        return self


class ImpactEstimate(BaseModel):
    expected_aqi_change: float | None = None
    expected_uhi_change: float | None = None
    expected_green_cover_change: float | None = None
    expected_carbon_reduction: float | None = None
    expected_health_risk_change: float | None = None
    units: dict[str, str] = Field(default_factory=dict)
    methodology: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    provenance: list[EstimateProvenance] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    uncertainty: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> ImpactEstimate:
        estimates = (
            self.expected_aqi_change,
            self.expected_uhi_change,
            self.expected_green_cover_change,
            self.expected_carbon_reduction,
            self.expected_health_risk_change,
        )
        if any(value is not None for value in estimates) and not self.provenance:
            raise ValueError("Numerical impact estimates require provenance.")
        return self


class ScenarioConstraints(BaseModel):
    budget_limit: float | None = Field(default=None, ge=0)
    currency: str = "INR"
    available_land_hectares: float | None = Field(default=None, ge=0)
    time_horizon_years: float | None = Field(default=None, gt=0)
    policy_constraints: list[str] = Field(default_factory=list)
    other: dict[str, Any] = Field(default_factory=dict)

    @field_validator("policy_constraints")
    @classmethod
    def strip_policy_constraints(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class ScenarioObjectives(BaseModel):
    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)


class InterventionDefinition(BaseModel):
    intervention_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str
    description: str
    target_problems: list[str]
    required_parameters: list[str] = Field(default_factory=list)
    optional_parameters: list[str] = Field(default_factory=list)
    applicable_contexts: list[str] = Field(default_factory=list)
    excluded_contexts: list[str] = Field(default_factory=list)
    cost_model: str | None = None
    impact_models: list[str] = Field(default_factory=list)
    policy_dependencies: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    version: str = "1.0"


class ScenarioIntervention(BaseModel):
    intervention_id: str
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    parameter_sources: dict[str, Literal["user_input", "dataset", "policy", "model", "configured_assumption"]] = Field(
        default_factory=dict
    )
    definition_version: str = "1.0"


class Scenario(BaseModel):
    scenario_id: str = Field(default_factory=lambda: f"SCN-{uuid4().hex[:12].upper()}")
    scenario_version: int = Field(default=1, ge=1)
    name: str
    description: str
    city: str
    zone: str | None = None
    intervention_type: str
    interventions: list[ScenarioIntervention] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    target_problems: list[str] = Field(default_factory=list)
    scale: dict[str, Any] = Field(default_factory=dict)
    implementation_parameters: dict[str, Any] = Field(default_factory=dict)
    constraint_values: ScenarioConstraints = Field(default_factory=ScenarioConstraints)
    required_resources: list[str] = Field(default_factory=list)
    estimated_cost: CostEstimate | None = None
    expected_impacts: ImpactEstimate | None = None
    carbon_reduction_availability_reason: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: Literal[
        "DRAFT",
        "VALIDATED",
        "INVALID",
        "SIMULATION_READY",
        "SIMULATED",
        "REJECTED",
        "REQUIRES_REVIEW",
    ] = "DRAFT"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provenance: dict[str, Any] = Field(default_factory=dict)


class ScenarioEvidence(BaseModel):
    evidence_id: str
    source: str
    source_type: str
    title: str | None = None
    url: str | None = None
    page: int | None = None
    note: str | None = None


class InterventionGenerationDiagnostic(BaseModel):
    requested_name: str
    canonical_intervention_id: str | None = None
    matched: bool
    rejected: bool
    reason: str


class ScenarioGenerationRequest(BaseModel):
    city: str | None = Field(default=None, min_length=1)
    zone: str | None = None
    problem_statement: str | None = None
    problems: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    constraints: ScenarioConstraints = Field(default_factory=ScenarioConstraints)
    requested_interventions: list[str] = Field(default_factory=list)
    implementation_period_years: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    intervention_parameters: dict[str, dict[str, Any]] = Field(default_factory=dict)
    parameter_variants: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    include_baseline: bool = True
    include_combinations: bool = True
    max_combination_size: int = Field(default=2, ge=1, le=3)
    max_scenarios: int = Field(default=8, ge=1, le=20)
    urban_state: UrbanState | None = None
    workflow_id: str | None = None
    urban_state_version: str | None = None

    @field_validator("problems", "objectives", "requested_interventions")
    @classmethod
    def clean_string_lists(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @model_validator(mode="after")
    def validate_context(self) -> ScenarioGenerationRequest:
        if self.urban_state is None:
            if not self.city or not self.city.strip():
                raise ValueError("city is required when urban_state is not provided")
            if not self.problem_statement and not self.problems:
                raise ValueError("problem_statement or at least one problem is required")
        oversized_variants = [
            key for key, variants in self.parameter_variants.items()
            if len(variants) > self.max_scenarios
        ]
        if oversized_variants:
            raise ValueError(
                "Parameter variant count cannot exceed max_scenarios for: "
                + ", ".join(sorted(oversized_variants))
            )
        return self


class ScenarioVersionRequest(BaseModel):
    parameter_updates: dict[str, dict[str, Any]] = Field(min_length=1)


class ScenarioSet(BaseModel):
    request_id: str = Field(default_factory=lambda: f"REQ-{uuid4().hex[:12].upper()}")
    workflow_id: str | None = None
    city: str
    zone: str | None = None
    problem_statement: str
    identified_problems: list[str] = Field(default_factory=list)
    objectives: ScenarioObjectives = Field(default_factory=ScenarioObjectives)
    constraints: ScenarioConstraints = Field(default_factory=ScenarioConstraints)
    scenarios: list[Scenario] = Field(default_factory=list)
    generation_method: str = "deterministic_catalog"
    intervention_catalog_version: str = "1.0"
    urban_state_version: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generation_duration_ms: float | None = Field(default=None, ge=0)
    evidence: list[ScenarioEvidence] = Field(default_factory=list)
    intervention_diagnostics: list[InterventionGenerationDiagnostic] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: Literal["completed", "partial"] = "completed"

    @model_validator(mode="after")
    def ensure_unique_scenarios(self) -> ScenarioSet:
        identifiers = [scenario.scenario_id for scenario in self.scenarios]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("scenario_id values must be unique within a ScenarioSet")
        return self
