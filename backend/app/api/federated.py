from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.federated.server import FEDERATED_STATUS, run_federated_simulation

router = APIRouter(prefix="/api/v1", tags=["federated-learning"])
logger = logging.getLogger(__name__)


class FederatedRunRequest(BaseModel):
    # Used to build a checkpoint directory name, so it must be a plain identifier
    # (no path separators or "..").
    model_name: str = Field(default="aqi_model", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    num_rounds: int = Field(default=2, ge=1, le=20)
    num_clients: int = Field(default=3, ge=2, le=10)
    local_epochs: int = Field(default=1, ge=1, le=10)


@router.post("/federated/start")
async def start_federated_learning(request: FederatedRunRequest) -> dict[str, Any]:
    try:
        result = run_federated_simulation(
            num_rounds=request.num_rounds,
            num_clients=request.num_clients,
            local_epochs=request.local_epochs,
            model_name=request.model_name,
        )
        return result
    except Exception as exc:  # pragma: no cover - API guard
        logger.exception("Federated training failed")
        raise HTTPException(status_code=500, detail="Federated training failed. See server logs.") from exc


@router.get("/federated/status")
async def federated_status() -> dict[str, Any]:
    return dict(FEDERATED_STATUS)


@router.get("/federated/metrics")
async def federated_metrics() -> dict[str, Any]:
    return {"metrics": FEDERATED_STATUS.get("metrics", {})}


@router.get("/federated/model")
async def federated_model() -> dict[str, Any]:
    return {
        "model_name": FEDERATED_STATUS.get("model_name", "aqi_model"),
        "model_version": FEDERATED_STATUS.get("model_version", "1.0"),
        "status": FEDERATED_STATUS.get("status", "IDLE"),
        "round": FEDERATED_STATUS.get("current_round", 0),
    }


__all__ = ["router"]
