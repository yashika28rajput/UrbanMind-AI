from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.tools.health_tools import predict_health_risk


def health_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "health_agent"
    state.health_analysis = predict_health_risk(
        city=state.request.city,
        zone=state.request.zone,
        aqi_prediction=state.forecasts.aqi_prediction if state.forecasts else None,
    )
    state.workflow_status = "health_complete"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["health_agent"]))
    state.next_agent = "economics_agent"
    return state
