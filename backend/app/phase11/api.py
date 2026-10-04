from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.phase11.engine import run_simulation
from app.phase11.repository import get_simulation, persist_simulation
from app.phase11.schemas import SimulationRequest, SimulationResult

router = APIRouter(prefix="/api/v1/simulation", tags=["digital-twin-simulation"])
logger = logging.getLogger(__name__)


@router.post("/run", response_model=SimulationResult)
async def simulate(request: SimulationRequest) -> SimulationResult:
    try:
        result = run_simulation(request)
        persist_simulation(result)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Could not persist simulation")
        raise HTTPException(status_code=503, detail="Simulation storage is unavailable.") from exc


@router.get("/{simulation_id}", response_model=SimulationResult)
async def get_simulation_result(simulation_id: str) -> SimulationResult:
    try:
        result = get_simulation(simulation_id)
    except SQLAlchemyError as exc:
        logger.exception("Could not retrieve simulation", extra={"simulation_id": simulation_id})
        raise HTTPException(status_code=503, detail="Simulation storage is unavailable.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")
    return SimulationResult.model_validate(result)
