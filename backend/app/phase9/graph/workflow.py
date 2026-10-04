from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.phase9.agents.critic_agent import critic_agent
from app.phase9.agents.data_agent import data_agent
from app.phase9.agents.economics_agent import economics_agent
from app.phase9.agents.environment_agent import environment_agent
from app.phase9.agents.forecast_agent import forecast_agent
from app.phase9.agents.health_agent import health_agent
from app.phase9.agents.optimization_agent import optimization_agent
from app.phase9.agents.policy_agent import policy_agent
from app.phase9.agents.report_agent import report_agent
from app.phase9.graph.state import UrbanState


def route_after_data(state: UrbanState) -> str:
    return "forecast_agent" if state.data_status.data_available else "report_agent"


def route_after_critic(state: UrbanState) -> str:
    if not state.critic_results or state.critic_results.critic_status == "passed":
        return "report_agent"
    if len(state.revisions) >= 2:
        return "report_agent"
    state.revisions.append("critic_revision")
    return "optimization_agent"


def build_workflow() -> StateGraph:
    graph = StateGraph(UrbanState)
    graph.add_node("data_agent", data_agent)
    graph.add_node("forecast_agent", forecast_agent)
    graph.add_node("environment_agent", environment_agent)
    graph.add_node("health_agent", health_agent)
    graph.add_node("economics_agent", economics_agent)
    graph.add_node("policy_agent", policy_agent)
    graph.add_node("optimization_agent", optimization_agent)
    graph.add_node("critic_agent", critic_agent)
    graph.add_node("report_agent", report_agent)

    graph.set_entry_point("data_agent")
    graph.add_conditional_edges("data_agent", route_after_data, {
        "forecast_agent": "forecast_agent",
        "report_agent": "report_agent",
    })
    graph.add_edge("forecast_agent", "environment_agent")
    graph.add_edge("environment_agent", "health_agent")
    graph.add_edge("health_agent", "economics_agent")
    graph.add_edge("economics_agent", "policy_agent")
    graph.add_edge("policy_agent", "optimization_agent")
    graph.add_edge("optimization_agent", "critic_agent")
    graph.add_conditional_edges("critic_agent", route_after_critic, {
        "optimization_agent": "optimization_agent",
        "report_agent": "report_agent",
    })
    graph.add_edge("report_agent", END)
    return graph


def analyze_urban_problem(request: Any) -> UrbanState:
    if hasattr(request, "model_dump"):
        payload = request.model_dump()
    elif isinstance(request, dict):
        payload = request
    else:
        payload = request.__dict__

    state = UrbanState(
        workflow_id=f"urbanmind_run_{abs(hash(payload.get('query', 'urbanmind')))}",
        request={
            "query": payload.get("query", "Analyze urban conditions."),
            "city": payload.get("city", "Delhi"),
            "zone": payload.get("zone", "Zone X"),
            "objective": payload.get("objective"),
            "constraints": payload.get("constraints", []),
            "requested_interventions": payload.get("requested_interventions", payload.get("interventions", [])),
            "scenario": payload.get("scenario"),
        },
    )
    graph = build_workflow()
    compiled = graph.compile()
    result = compiled.invoke(state)
    if isinstance(result, dict):
        return UrbanState.model_validate(result)
    return result
