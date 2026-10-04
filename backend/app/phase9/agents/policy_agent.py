from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.tools.policy_tools import query_policy_rag


def policy_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "policy_agent"
    state.policy_analysis = query_policy_rag(
        city=state.request.city,
        zone=state.request.zone,
        interventions=state.candidate_interventions or state.request.requested_interventions or ["Green Infrastructure"],
    )
    state.workflow_status = "policy_complete"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["policy_agent"]))
    state.next_agent = "optimization_agent"
    return state
