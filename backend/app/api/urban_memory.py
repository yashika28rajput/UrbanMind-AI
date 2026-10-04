import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.urban_memory import (
    MemoryType,
    UrbanMemoryCreate,
    UrbanMemoryOutcomeUpdate,
    UrbanMemorySearch,
)
from app.services.urban_memory import (
    create_memory,
    get_memory,
    get_memory_status,
    list_memories,
    search_memories,
    update_memory_outcome,
)

router = APIRouter(prefix="/api/v1/memory", tags=["urban-memory"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def memory_status() -> dict[str, object]:
    try:
        return get_memory_status()
    except (SQLAlchemyError, OSError, RuntimeError, ImportError) as exc:
        logger.exception("Urban memory status check failed")
        raise HTTPException(status_code=503, detail="Urban memory storage is unavailable.") from exc


@router.post("/memories", status_code=201)
async def create_memory_endpoint(request: UrbanMemoryCreate) -> dict[str, object]:
    try:
        result = create_memory(**request.model_dump())
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError, RuntimeError, ImportError) as exc:
        logger.exception("Could not store urban memory")
        raise HTTPException(status_code=503, detail="Could not store urban memory.") from exc


@router.get("/memories")
async def list_memories_endpoint(
    memory_type: MemoryType | None = None,
    city: str | None = None,
    zone: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    try:
        memories = list_memories(
            memory_type=memory_type,
            city=city,
            zone=zone,
            limit=limit,
            offset=offset,
        )
        return {"count": len(memories), "limit": limit, "offset": offset, "memories": memories}
    except (SQLAlchemyError, OSError) as exc:
        logger.exception("Could not read urban memories")
        raise HTTPException(status_code=503, detail="Could not read urban memories.") from exc


@router.get("/memories/{memory_id}")
async def get_memory_endpoint(memory_id: str) -> dict[str, object]:
    try:
        memory = get_memory(memory_id)
    except (SQLAlchemyError, OSError) as exc:
        logger.exception("Could not read urban memory")
        raise HTTPException(status_code=503, detail="Could not read urban memory.") from exc
    if memory is None:
        raise HTTPException(status_code=404, detail="Urban memory not found.")
    return memory


@router.patch("/memories/{memory_id}/outcome")
async def update_memory_outcome_endpoint(
    memory_id: str,
    request: UrbanMemoryOutcomeUpdate,
) -> dict[str, object]:
    try:
        memory = update_memory_outcome(memory_id, **request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError, RuntimeError, ImportError) as exc:
        logger.exception("Could not record intervention outcome")
        raise HTTPException(status_code=503, detail="Could not record intervention outcome.") from exc
    if memory is None:
        raise HTTPException(status_code=404, detail="Urban memory not found.")
    return memory


@router.post("/search")
async def search_memories_endpoint(request: UrbanMemorySearch) -> dict[str, object]:
    try:
        results = search_memories(**request.model_dump())
        return {"query": request.query, "count": len(results), "results": results}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError, RuntimeError, ImportError) as exc:
        logger.exception("Could not search urban memories")
        raise HTTPException(status_code=503, detail="Could not search urban memories.") from exc
