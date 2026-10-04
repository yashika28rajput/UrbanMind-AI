from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.tools.forecast_tools import predict_aqi, predict_uhi


def forecast_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "forecast_agent"
    forecast = predict_aqi(state.request.city, state.request.zone)
    forecast.uhi_prediction = predict_uhi(state.request.city, state.request.zone)
    state.forecasts = forecast
    state.workflow_status = "forecast_complete"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["forecast_agent"]))
    state.next_agent = "environment_agent"
    return state
