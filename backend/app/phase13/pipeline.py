from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import Field

from app.phase10.graph import run_scenario_workflow
from app.phase10.repository import persist_scenario_set
from app.phase10.schemas import ScenarioGenerationRequest, ScenarioSet
from app.phase11.engine import run_simulation
from app.phase11.repository import persist_simulation
from app.phase11.schemas import SimulationInput, SimulationRequest, SimulationResult
from app.phase12.engine import run_optimization
from app.phase12.repository import persist_optimization
from app.phase12.schemas import (
    ConstraintDefinition,
    ObjectiveDefinition,
    OptimizationRequest,
    OptimizationResult,
)
from app.phase13.engine import explain_recommendation
from app.phase13.schemas import (
    RecommendationExplanationRequest,
    RecommendationExplanationResult,
)


class PipelineRequest(ScenarioGenerationRequest):
    simulation_input: SimulationInput = Field(default_factory=SimulationInput)
    optimization_objectives: list[ObjectiveDefinition] = Field(min_length=1)
    optimization_constraints: list[ConstraintDefinition] = Field(default_factory=list)
    decision_preferences: dict[str, float] = Field(default_factory=dict)


class PipelineResult(ScenarioSet):
    simulations: list[SimulationResult] = Field(default_factory=list)
    optimization: OptimizationResult | None = None
    explanation: RecommendationExplanationResult | None = None
    final_report: dict[str, Any] = Field(default_factory=dict)


class PipelineState(TypedDict, total=False):
    request: PipelineRequest
    scenarios: ScenarioSet
    simulations: list[SimulationResult]
    optimization: OptimizationResult
    explanation: RecommendationExplanationResult
    result: PipelineResult


def _generate(state: PipelineState) -> dict[str, Any]:
    request = state["request"]
    scenario_request = ScenarioGenerationRequest.model_validate(
        request.model_dump(exclude={
            "simulation_input",
            "optimization_objectives",
            "optimization_constraints",
            "decision_preferences",
        })
    )
    scenarios = run_scenario_workflow(scenario_request)
    persist_scenario_set(scenarios)
    return {"scenarios": scenarios}


def _simulate(state: PipelineState) -> dict[str, Any]:
    request = state["request"]
    scenarios = state["scenarios"]
    urban_state = request.urban_state
    if urban_state is None:
        from app.phase9.graph.state import UrbanState

        urban_state = UrbanState(
            workflow_id=scenarios.workflow_id or "phase13_pipeline",
            request={
                "query": request.problem_statement or ", ".join(request.problems),
                "city": request.city or scenarios.city,
                "zone": request.zone or scenarios.zone or "",
            },
        )
    results = []
    for scenario in scenarios.scenarios:
        if scenario.status == "INVALID":
            continue
        result = run_simulation(SimulationRequest(
            urban_state=urban_state,
            scenario=scenario,
            simulation_input=request.simulation_input,
        ))
        persist_simulation(result)
        results.append(result)
    if not results:
        raise ValueError("No valid scenarios are available for simulation.")
    return {"simulations": results}


def _optimize(state: PipelineState) -> dict[str, Any]:
    request = state["request"]
    result = run_optimization(OptimizationRequest(
        simulations=state["simulations"],
        objectives=request.optimization_objectives,
        constraints=request.optimization_constraints,
        decision_preferences=request.decision_preferences,
    ))
    persist_optimization(result)
    return {"optimization": result}


def _explain(state: PipelineState) -> dict[str, Any]:
    result = explain_recommendation(RecommendationExplanationRequest(
        simulations=state["simulations"],
        optimization_result=state["optimization"],
    ))
    return {"explanation": result}


def _report(state: PipelineState) -> dict[str, Any]:
    scenarios = state["scenarios"]
    optimization = state["optimization"]
    explanation = state["explanation"]
    summary = {
        "city": scenarios.city,
        "zone": scenarios.zone,
        "problem_statement": scenarios.problem_statement,
        "pareto_scenario_ids": [item.scenario_id for item in optimization.pareto_solutions],
        "pareto_strategies": [
            item.model_dump(mode="json") for item in optimization.pareto_solutions
        ],
        "dominated_scenario_ids": [item.scenario_id for item in optimization.dominated_strategies],
        "infeasible_scenario_ids": [item.scenario_id for item in optimization.infeasible_strategies],
        "preferred_scenario_id": explanation.preferred_scenario_id,
        "reasons": explanation.reasons,
        "tradeoffs": explanation.tradeoffs,
        "strategy_explanations": [
            item.model_dump(mode="json") for item in explanation.strategy_explanations
        ],
        "limitations": list(dict.fromkeys(scenarios.warnings + explanation.limitations)),
    }
    result = PipelineResult(
        **scenarios.model_dump(),
        simulations=state["simulations"],
        optimization=optimization,
        explanation=explanation,
        final_report=summary,
    )
    return {"result": result}


def build_pipeline_workflow() -> Any:
    graph = StateGraph(PipelineState)
    graph.add_node("scenario_generation", _generate)
    graph.add_node("digital_twin_simulation", _simulate)
    graph.add_node("multi_objective_optimization", _optimize)
    graph.add_node("explainability", _explain)
    graph.add_node("final_report", _report)
    graph.set_entry_point("scenario_generation")
    graph.add_edge("scenario_generation", "digital_twin_simulation")
    graph.add_edge("digital_twin_simulation", "multi_objective_optimization")
    graph.add_edge("multi_objective_optimization", "explainability")
    graph.add_edge("explainability", "final_report")
    graph.add_edge("final_report", END)
    return graph.compile()


def run_pipeline(request: PipelineRequest) -> PipelineResult:
    return build_pipeline_workflow().invoke({"request": request})["result"]
