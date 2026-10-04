from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.tools.optimization_tools import run_optimization


def optimization_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "optimization_agent"
    interventions = state.candidate_interventions or state.request.requested_interventions or ["Green Infrastructure", "Public Transport Improvement"]
    state.optimization_results = run_optimization(interventions, objective=state.request.objective)
    state.workflow_status = "optimization_complete"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["optimization_agent"]))
    state.next_agent = "critic_agent"
    return state
