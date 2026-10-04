from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.tools.data_tools import validate_data


def data_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "data_agent"
    state.data_status = validate_data(
        city=state.request.city,
        zone=state.request.zone,
        requested_interventions=state.request.requested_interventions,
    )
    state.workflow_status = "data_validated"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["data_agent"]))
    state.next_agent = "forecast_agent"
    return state
