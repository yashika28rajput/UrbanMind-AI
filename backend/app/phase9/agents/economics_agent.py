from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.tools.economics_tools import estimate_intervention_cost


def economics_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "economics_agent"
    state.economic_analysis = estimate_intervention_cost(
        state.candidate_interventions or state.request.requested_interventions or ["Green Infrastructure"],
    )
    state.workflow_status = "economics_complete"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["economics_agent"]))
    state.next_agent = "policy_agent"
    return state
