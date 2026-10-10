from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.phase11.schemas import SimulationResult


class ObjectiveDefinition(BaseModel):
    name: str = Field(min_length=1)
    direction: Literal["minimize", "maximize"]
    weight: float | None = Field(default=None, gt=0)


class ConstraintDefinition(BaseModel):
    name: str = Field(min_length=1)
    metric: str
    operator: Literal["<=", ">="]
    value: float
    policy: bool = False


class OptimizationRequest(BaseModel):
    simulations: list[SimulationResult]
    objectives: list[ObjectiveDefinition] = Field(min_length=1)
    constraints: list[ConstraintDefinition] = Field(default_factory=list)
    decision_preferences: dict[str, float] = Field(default_factory=dict)


class ScenarioScore(BaseModel):
    scenario_id: str
    simulation_id: str
    objective_values: dict[str, float | None]
    objective_sources: dict[str, str] = Field(default_factory=dict)
    feasible: bool
    constraint_violations: list[str] = Field(default_factory=list)
    missing_objectives: list[str] = Field(default_factory=list)
    pareto_rank: int | None = None
    crowding_distance: float | None = None
    crowding_boundary: bool = False
    decision_score: float | None = None


class ParetoSolution(BaseModel):
    scenario_id: str
    simulation_id: str
    objective_values: dict[str, float]
    objective_sources: dict[str, str] = Field(default_factory=dict)
    constraint_violations: list[str] = Field(default_factory=list)
    pareto_rank: int = 1
    crowding_distance: float | None = None
    crowding_boundary: bool = False
    decision_score: float | None = None


class OptimizationResult(BaseModel):
    optimization_id: str = Field(default_factory=lambda: f"OPT-{uuid4().hex[:12].upper()}")
    status: str
    algorithm: str = "NSGA-II non-dominated sorting and crowding distance"
    objectives: list[ObjectiveDefinition]
    constraints: list[ConstraintDefinition]
    pareto_solutions: list[ParetoSolution]
    dominated_strategies: list[ScenarioScore]
    infeasible_strategies: list[ScenarioScore]
    unevaluable_strategies: list[ScenarioScore] = Field(default_factory=list)
    scores: list[ScenarioScore]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decision_preferences: dict[str, float] = Field(default_factory=dict)
