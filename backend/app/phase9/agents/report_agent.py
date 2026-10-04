from __future__ import annotations

from app.phase9.graph.state import UrbanState
from app.phase9.schemas import EvidenceSource, ReportResult


def report_agent(state: UrbanState) -> UrbanState:
    state.current_agent = "report_agent"
    evidence = [
        EvidenceSource(source="UrbanMind mock data layer", type="dataset", note="Deterministic mock evidence for phase 9 workflow."),
        EvidenceSource(source="Policy and health evidence registry", type="document", note="Grounded through the local evidence layer."),
    ]
    state.evidence = evidence
    state.sources = [item.source for item in evidence]
    state.final_report = ReportResult(
        executive_summary=(
            f"{state.request.city} {state.request.zone} is evaluated through a multi-agent decision flow. "
            f"The workflow combines data validation, forecasting, environmental, health, economic, and policy analysis."
        ),
        problem_statement=state.request.query,
        baseline=f"Current analysis indicates elevated urban risk for {state.request.city} in {state.request.zone}.",
        findings=[
            "Data quality checks passed for the deterministic workflow.",
            "Forecast signals indicate elevated AQI exposure.",
            "Environmental and health risks require intervention review.",
        ],
        evaluated_interventions=state.optimization_results.selected_interventions if state.optimization_results else state.request.requested_interventions,
        tradeoffs=["Environmental benefit must be balanced against cost and policy feasibility."],
        evidence=evidence,
        limitations=["This is a deterministic mock workflow and not production-grade evidence generation."],
        uncertainty=["Forecast values are mock estimates intended for architecture validation."],
        recommended_next_steps=["Validate these results against real urban datasets and policy regulations before action."],
    )
    state.workflow_status = "completed"
    state.completed_agents = list(dict.fromkeys(state.completed_agents + ["report_agent"]))
    state.next_agent = None
    return state
