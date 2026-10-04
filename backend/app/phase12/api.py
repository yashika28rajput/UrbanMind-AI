from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.phase12.engine import run_optimization
from app.phase12.repository import get_optimization, persist_optimization
from app.phase12.schemas import OptimizationRequest, OptimizationResult

router = APIRouter(prefix="/api/v1/optimization", tags=["multi-objective-optimization"])
logger = logging.getLogger(__name__)


@router.post("/run", response_model=OptimizationResult)
async def optimize(request: OptimizationRequest) -> OptimizationResult:
    try:
        result = run_optimization(request)
        persist_optimization(result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Could not persist optimization")
        raise HTTPException(status_code=503, detail="Optimization storage is unavailable.") from exc


@router.get("/{optimization_id}", response_model=OptimizationResult)
async def get_optimization_result(optimization_id: str) -> OptimizationResult:
    try:
        result = get_optimization(optimization_id)
    except SQLAlchemyError as exc:
        logger.exception("Could not retrieve optimization", extra={"optimization_id": optimization_id})
        raise HTTPException(status_code=503, detail="Optimization storage is unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Optimization not found.")
    return OptimizationResult.model_validate(result)


@router.get("/{optimization_id}/pareto")
async def get_pareto_frontier(optimization_id: str) -> dict[str, object]:
    try:
        result = get_optimization(optimization_id)
    except SQLAlchemyError as exc:
        logger.exception("Could not retrieve Pareto frontier", extra={"optimization_id": optimization_id})
        raise HTTPException(status_code=503, detail="Optimization storage is unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Optimization not found.")
    optimization = OptimizationResult.model_validate(result)
    return {
        "optimization_id": optimization.optimization_id,
        "objectives": [objective.model_dump() for objective in optimization.objectives],
        "pareto_solutions": [solution.model_dump() for solution in optimization.pareto_solutions],
    }
