from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.carbon_service import CarbonCalculationRequest, calculate_carbon_reduction

router = APIRouter(prefix="/api/v1", tags=["carbon"])


@router.post("/carbon/calculate")
async def calculate_carbon(request: CarbonCalculationRequest) -> dict[str, Any]:
    """Emissions = quantity x emission factor; reduction = baseline - projected.

    Emission factors are never defaulted: each activity must supply its own factor and source.
    """
    try:
        return calculate_carbon_reduction(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
