from __future__ import annotations

import logging
from time import perf_counter
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph

from app.phase10.engine import detect_problems, generate_scenario_set, identify_objectives
from app.phase10.schemas import ScenarioEvidence, ScenarioGenerationRequest, ScenarioObjectives, ScenarioSet
from app.phase9.graph.state import UrbanState
from app.services.knowledge_graph import get_graph_context, get_interventions_for_pollutant
from app.services.rag_service import search_documents

logger = logging.getLogger(__name__)


class ScenarioGraphState(TypedDict, total=False):
    urban_state: UrbanState
    request: ScenarioGenerationRequest
    problems: list[str]
    objectives: ScenarioObjectives
    evidence: list[ScenarioEvidence]
    knowledge_graph_interventions: list[str]
    warnings: list[str]
    scenario_set: ScenarioSet


def _detect_context(state: ScenarioGraphState) -> dict[str, Any]:
    problems, warnings = detect_problems(state["urban_state"], state["request"])
    return {
        "problems": problems,
        "objectives": identify_objectives(problems, state["request"].objectives),
        "warnings": warnings,
    }


def _retrieve_evidence(state: ScenarioGraphState) -> dict[str, Any]:
    request = state["request"]
    urban_state = state["urban_state"]
    problem_text = request.problem_statement or urban_state.request.query
    query = f"{problem_text} urban interventions"
    evidence: list[ScenarioEvidence] = []
    warnings = list(state.get("warnings", []))
    try:
        documents = search_documents(
            query=query,
            city=request.city or urban_state.request.city,
            zone=request.zone if request.zone is not None else urban_state.request.zone,
            top_k=5,
        )
        evidence.extend(
            ScenarioEvidence(
                evidence_id=str(item["document_id"]),
                source=str(item.get("source") or item["document_id"]),
                source_type=str(item.get("document_type") or "document"),
                title=item.get("title"),
                url=item.get("url"),
                page=item.get("page"),
            )
            for item in documents
        )
        if not documents:
            warnings.append("Evidence retrieval returned no indexed documents; no evidence was attributed.")
    except Exception:
        logger.exception(
            "Scenario evidence retrieval failed",
            extra={"workflow_id": urban_state.workflow_id, "city": request.city},
        )
        warnings.append("Evidence retrieval was unavailable; no evidence was attributed.")

    kg_interventions: list[str] = []
    pollutants = {
        {"high_pm25": "PM2.5", "high_aqi": "PM2.5"}.get(problem)
        for problem in state.get("problems", [])
    }
    try:
        for pollutant in sorted(item for item in pollutants if item):
            kg_interventions.extend(get_interventions_for_pollutant(pollutant))
            for relation in get_graph_context(
                city=request.city or urban_state.request.city,
                pollutant=pollutant,
            ):
                evidence_id = "kg:" + ":".join(
                    str(relation.get(key, "")) for key in ("entity", "relationship", "target")
                )
                evidence.append(ScenarioEvidence(
                    evidence_id=evidence_id,
                    source="UrbanMind knowledge graph",
                    source_type="knowledge_graph",
                    title=f"{relation.get('entity', '')} {relation.get('relationship', '')} {relation.get('target', '')}".strip(),
                ))
    except Exception:
        logger.exception(
            "Knowledge graph retrieval failed",
            extra={"workflow_id": urban_state.workflow_id, "city": request.city},
        )
        warnings.append("Knowledge graph retrieval was unavailable; catalog matching was used.")
    evidence_by_id = {item.evidence_id: item for item in evidence}
    return {
        "evidence": list(evidence_by_id.values()),
        "knowledge_graph_interventions": list(dict.fromkeys(kg_interventions)),
        "warnings": list(dict.fromkeys(warnings)),
    }


def _construct_scenarios(state: ScenarioGraphState) -> dict[str, Any]:
    result = generate_scenario_set(
        state["urban_state"],
        state["request"],
        evidence=state.get("evidence", []),
        knowledge_graph_interventions=state.get("knowledge_graph_interventions", []),
        warnings=state.get("warnings", []),
    )
    result.objectives = state["objectives"]
    return {"scenario_set": result}


def build_scenario_workflow() -> Any:
    graph = StateGraph(ScenarioGraphState)
    graph.add_node("detect_problems_and_objectives", _detect_context)
    graph.add_node("retrieve_knowledge_and_evidence", _retrieve_evidence)
    graph.add_node("construct_and_validate_scenarios", _construct_scenarios)
    graph.set_entry_point("detect_problems_and_objectives")
    graph.add_edge("detect_problems_and_objectives", "retrieve_knowledge_and_evidence")
    graph.add_edge("retrieve_knowledge_and_evidence", "construct_and_validate_scenarios")
    graph.add_edge("construct_and_validate_scenarios", END)
    return graph.compile()


def run_scenario_workflow(request: ScenarioGenerationRequest) -> ScenarioSet:
    workflow_id = request.workflow_id or f"scenario_workflow_{uuid4().hex[:12]}"
    started_at = perf_counter()
    urban_state = request.urban_state or UrbanState(
        workflow_id=workflow_id,
        request={
            "query": request.problem_statement or ", ".join(request.problems),
            "city": request.city or "",
            "zone": request.zone or "",
            "objective": request.objectives[0] if request.objectives else None,
            "requested_interventions": request.requested_interventions,
        },
    )
    result = build_scenario_workflow().invoke({"urban_state": urban_state, "request": request})
    scenario_set = result["scenario_set"]
    scenario_set.generation_duration_ms = (perf_counter() - started_at) * 1000
    return scenario_set
