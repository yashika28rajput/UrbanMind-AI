from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.urban_memory_store import Base, SessionLocal, initialize_database
from app.phase12.schemas import OptimizationResult


class OptimizationRecord(Base):
    __tablename__ = "optimization_runs"

    optimization_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


def persist_optimization(result: OptimizationResult) -> None:
    initialize_database()
    with SessionLocal() as session:
        session.add(OptimizationRecord(
            optimization_id=result.optimization_id,
            result=result.model_dump(mode="json"),
        ))
        session.commit()


def get_optimization(optimization_id: str) -> dict[str, Any] | None:
    initialize_database()
    with SessionLocal() as session:
        record = session.get(OptimizationRecord, optimization_id)
        return dict(record.result) if record else None
