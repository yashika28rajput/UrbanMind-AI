from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.knowledge_graph import (
    get_graph_context,
    get_interventions_for_pollutant,
    get_policies_for_intervention,
    get_related_entities,
    knowledge_graph_service,
)
from app.services.rag_service import answer_rag_query, rag_status, search_documents

router = APIRouter(prefix="/api/v1", tags=["knowledge-and-rag"])


class GraphQueryRequest(BaseModel):
    entity: str
    entity_type: str | None = None
    relationship: str | None = None
    target_type: str | None = None


class RAGQueryRequest(BaseModel):
    query: str
    city: str | None = None
    zone: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


@router.get("/knowledge-graph/status")
async def knowledge_graph_status() -> dict[str, object]:
    return {
        "status": "ready",
        "backend": "in_memory_fallback",
        "entity_count": knowledge_graph_service.entity_count,
        "relationship_count": knowledge_graph_service.relationship_count,
        "mode": "fallback",
    }


@router.post("/knowledge-graph/query")
async def knowledge_graph_query(request: GraphQueryRequest) -> dict[str, object]:
    if not request.entity.strip():
        raise HTTPException(status_code=400, detail="Entity must not be empty.")
    results = get_related_entities(
        entity=request.entity.strip(),
        entity_type=request.entity_type,
        relationship=request.relationship,
        target_type=request.target_type,
    )
    return {
        "entity": request.entity.strip(),
        "count": len(results),
        "results": results,
    }


@router.post("/rag/query")
async def rag_query(request: RAGQueryRequest) -> dict[str, object]:
    try:
        return answer_rag_query(query=request.query, city=request.city, zone=request.zone, top_k=request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rag/health")
async def rag_health() -> dict[str, object]:
    status = rag_status()
    return {
        **status,
        "backend": "qdrant" if status["mode"] == "qdrant" else "in_memory_vector_store",
        "grounding": "retrieval_based",
    }


@router.get("/knowledge-graph/interventions/{pollutant}")
async def interventions_for_pollutant(pollutant: str) -> dict[str, object]:
    return {"pollutant": pollutant, "interventions": get_interventions_for_pollutant(pollutant)}


@router.get("/knowledge-graph/policies/{intervention}")
async def policies_for_intervention(intervention: str) -> dict[str, object]:
    return {"intervention": intervention, "policies": get_policies_for_intervention(intervention)}


@router.get("/knowledge-graph/context")
async def knowledge_graph_context(city: str | None = None, pollutant: str | None = None, intervention: str | None = None) -> dict[str, object]:
    return {"context": get_graph_context(city=city, pollutant=pollutant, intervention=intervention)}


@router.post("/rag/search")
async def rag_search(request: RAGQueryRequest) -> dict[str, object]:
    try:
        results = search_documents(
            query=request.query,
            city=request.city,
            zone=request.zone,
            top_k=request.top_k,
        )
        return {"query": request.query, "count": len(results), "results": results}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
