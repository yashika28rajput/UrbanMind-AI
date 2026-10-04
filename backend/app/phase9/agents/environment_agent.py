from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.tools.environment_tools import simulate_environmental_impact


def environment_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "environment_agent"
    interventions = state.candidate_interventions or state.request.requested_interventions or ["Green Infrastructure"]
    state.environmental_analysis = simulate_environmental_impact(
        city=state.request.city,
        zone=state.request.zone,
        interventions=interventions,
    )
    state.workflow_status = "environment_complete"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["environment_agent"]))
    state.next_agent = "health_agent"
    return state
