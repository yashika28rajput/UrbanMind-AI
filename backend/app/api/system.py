from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database.urban_memory_store import engine
from app.digital_twin.service import get_virtual_city_model
from app.services.rag_service import rag_status

router = APIRouter(prefix="/api/v1", tags=["system"])
logger = logging.getLogger(__name__)
PROJECT_DIR = Path(__file__).resolve().parents[3]


@router.get("/system/status")
async def system_status() -> dict[str, object]:
    services: dict[str, dict[str, object]] = {}

    started = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        services["database"] = {
            "status": "HEALTHY",
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "backend": engine.dialect.name,
        }
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        services["database"] = {"status": "UNAVAILABLE", "backend": engine.dialect.name}

    rag = rag_status()
    services["rag"] = {"status": rag["status"], "mode": rag["mode"]}
    services["qdrant"] = {"status": rag["qdrant_status"], "mode": rag["mode"]}

    try:
        model = get_virtual_city_model()
        services["digital_twin"] = {
            "status": "HEALTHY" if model.get("wards") else "UNAVAILABLE",
            "ward_count": len(model.get("wards", [])),
        }
    except (OSError, ValueError, KeyError):
        logger.exception("Digital Twin health check failed")
        services["digital_twin"] = {"status": "UNAVAILABLE"}

    model_files = list((PROJECT_DIR / "models").rglob("*_model_info.json"))
    services["ml_models"] = {
        "status": "HEALTHY" if model_files else "NOT_CONFIGURED",
        "count": len(model_files),
    }
    services["fastapi"] = {"status": "HEALTHY"}
    statuses = [str(item["status"]) for item in services.values()]
    overall = (
        "UNAVAILABLE" if "UNAVAILABLE" in statuses
        else "DEGRADED" if any(status not in {"HEALTHY", "NOT_CONFIGURED"} for status in statuses)
        else "DEGRADED" if any(status == "NOT_CONFIGURED" for status in statuses)
        else "HEALTHY"
    )
    return {
        "overall_status": overall,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "service": "UrbanMind AI",
        "version": "v1",
        "components": services,
    }
