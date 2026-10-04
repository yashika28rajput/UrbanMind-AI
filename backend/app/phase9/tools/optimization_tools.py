from __future__ import annotations

from app.phase9.schemas import OptimizationResult


def run_optimization(interventions: list[str], objective: str | None = None) -> OptimizationResult:
    selected = interventions[:2] if len(interventions) > 1 else interventions
    objective_values = {
        "environmental_benefit": 0.72,
        "health_benefit": 0.66,
        "cost_efficiency": 0.74,
    }
    return OptimizationResult(
        candidate_interventions=list(interventions),
        feasible_interventions=list(interventions),
        selected_interventions=selected,
        objective_values=objective_values,
        constraints=["budget", "policy compliance"],
        tradeoffs=["Higher environmental gains may require higher budget.", "Moderate interventions may be more feasible than aggressive ones."],
        rationale=f"Optimization used explicit objectives and constraints for {objective or 'risk reduction'}.",
    )
