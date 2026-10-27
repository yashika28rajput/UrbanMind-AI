from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.carbon_service import CarbonCalculationRequest, calculate_carbon_reduction
from app.services.ward_carbon_data import load_annual_ward_carbon

router = APIRouter(prefix="/api/v1", tags=["carbon"])


@router.get("/carbon/wards/annual")
async def annual_ward_carbon() -> dict[str, Any]:
    """Return the standalone, modelled 2021 annual ward road-traffic CO2 table."""
    try:
        return load_annual_ward_carbon()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Annual ward carbon data unavailable: {exc}") from exc


@router.post("/carbon/calculate")
async def calculate_carbon(request: CarbonCalculationRequest) -> dict[str, Any]:
    """Emissions = quantity x emission factor; reduction = baseline - projected.

    Emission factors are never defaulted: each activity must supply its own factor and source.
    """
    try:
        return calculate_carbon_reduction(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
