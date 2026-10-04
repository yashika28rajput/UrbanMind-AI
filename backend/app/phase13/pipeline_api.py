from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.phase13.pipeline import PipelineRequest, PipelineResult, run_pipeline

router = APIRouter(prefix="/api/v1/pipeline", tags=["decision-pipeline"])
logger = logging.getLogger(__name__)


@router.post("/run", response_model=PipelineResult)
async def run_decision_pipeline(request: PipelineRequest) -> PipelineResult:
    try:
        return run_pipeline(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Decision pipeline persistence failed")
        raise HTTPException(status_code=503, detail="Pipeline storage is unavailable.") from exc
