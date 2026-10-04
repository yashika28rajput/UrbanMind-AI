from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.schemas import CriticResult


def critic_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "critic_agent"
    issues = []
    if state.forecasts is None:
        issues.append("Forecasts were not generated.")
    if state.policy_analysis is None:
        issues.append("Policy evaluation is missing.")
    if state.optimization_results is None:
        issues.append("Optimization results are missing.")
    if state.economic_analysis is not None and state.economic_analysis.estimated_cost is None:
        issues.append("Economic cost estimate is incomplete.")

    critic = CriticResult(
        issues=issues,
        unsupported_claims=[],
        missing_evidence=[],
        constraint_violations=[],
        model_uncertainty=["Confidence values are synthetic placeholders in the deterministic mock workflow."],
        contradictory_results=[],
        recommended_revisions=["Review the policy fit and cost assumptions before finalizing the recommendation."],
        critic_status="needs_revision" if issues else "passed",
    )
    state.critic_results = critic
    state.workflow_status = "critic_complete"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["critic_agent"]))
    state.next_agent = "report_agent" if not issues else "optimization_agent"
    return state
