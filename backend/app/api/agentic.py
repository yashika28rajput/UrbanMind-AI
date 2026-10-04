from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.phase9.graph.workflow import analyze_urban_problem

router = APIRouter(prefix="/api/v1", tags=["multi-agent-workflow"])


class AgenticAnalysisRequest(BaseModel):
    query: str = Field(..., min_length=1)
    city: str = "Delhi"
    zone: str = "Zone X"
    objective: str | None = None
    constraints: list[str] = Field(default_factory=list)
    requested_interventions: list[str] = Field(default_factory=list)
    scenario: str | None = None


@router.post("/agentic/analyze")
async def analyze_agentic(request: AgenticAnalysisRequest) -> dict[str, Any]:
    try:
        state = analyze_urban_problem(request)
        return {
            "workflow_id": state.workflow_id,
            "status": state.workflow_status,
            "summary": state.final_report.executive_summary if state.final_report else "Analysis complete.",
            "findings": state.final_report.findings if state.final_report else [],
            "interventions": state.optimization_results.selected_interventions if state.optimization_results else state.request.requested_interventions,
            "critic": state.critic_results.model_dump() if state.critic_results else {},
            "sources": state.sources,
            "uncertainty": state.final_report.uncertainty if state.final_report else [],
            "limitations": state.final_report.limitations if state.final_report else [],
        }
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=500, detail=f"Agentic analysis failed: {exc}") from exc


@router.post("/decision/analyze")
async def analyze_decision(request: AgenticAnalysisRequest) -> dict[str, Any]:
    try:
        state = analyze_urban_problem(request)
        return {
            "current_state": state.request.model_dump() if hasattr(state.request, "model_dump") else state.request,
            "detected_problems": state.final_report.findings if state.final_report else [],
            "scenarios": state.request.requested_interventions,
            "simulation_results": state.forecasts.model_dump() if state.forecasts else {},
            "pareto_strategies": state.optimization_results.selected_interventions if state.optimization_results else [],
            "recommendation": state.final_report.executive_summary if state.final_report else "Analysis complete.",
            "explanation": state.final_report.model_dump() if state.final_report else {},
            "evidence": state.sources,
            "limitations": state.final_report.limitations if state.final_report else [],
        }
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=500, detail=f"Decision analysis failed: {exc}") from exc


@router.post("/recommendation")
async def build_recommendation(request: AgenticAnalysisRequest) -> dict[str, Any]:
    state = analyze_urban_problem(request)
    optimization = state.optimization_results
    report = state.final_report
    reasons = report.findings if report else []
    payload: dict[str, Any] = {
        "recommendation": report.executive_summary if report else "Recommendation generated from the urban analysis.",
        "alternatives": optimization.feasible_interventions if optimization else state.request.requested_interventions,
        "reasons": reasons,
        "expected_impacts": {
            "aqi": getattr(state.forecasts, "aqi_prediction", None) if state.forecasts else None,
            "uhi": getattr(state.forecasts, "uhi_prediction", None) if state.forecasts else None,
        },
        "cost": state.economic_analysis.estimated_cost if state.economic_analysis else None,
        "constraints": optimization.constraints if optimization else state.request.constraints,
        "evidence": state.sources,
        "limitations": report.limitations if report else [],
    }
    if state.forecasts and state.forecasts.confidence is not None:
        payload["confidence_or_uncertainty"] = state.forecasts.confidence
    return payload
