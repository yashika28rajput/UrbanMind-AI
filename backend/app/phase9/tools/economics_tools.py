from __future__ import annotations

from app.phase9.schemas import EconomicResult


def estimate_intervention_cost(interventions: list[str]) -> EconomicResult:
    estimate = 1200000.0 * max(1, len(interventions))
    return EconomicResult(
        estimated_cost=round(estimate, 2),
        operating_cost=round(estimate * 0.18, 2),
        maintenance_cost=round(estimate * 0.12, 2),
        cost_assumptions=["Mock unit cost model based on intervention scale.", "Costs represent planning-order estimates."],
        cost_range=[round(estimate * 0.8, 2), round(estimate * 1.25, 2)],
        uncertainty="moderate",
    )
