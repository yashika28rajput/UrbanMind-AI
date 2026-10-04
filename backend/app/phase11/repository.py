from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.urban_memory_store import Base, SessionLocal, initialize_database
from app.phase11.schemas import SimulationResult


class SimulationRecord(Base):
    __tablename__ = "simulations"

    simulation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scenario_version: Mapped[int] = mapped_column(nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


def persist_simulation(result: SimulationResult) -> None:
    initialize_database()
    with SessionLocal() as session:
        session.add(SimulationRecord(
            simulation_id=result.simulation_id,
            scenario_id=result.scenario_id,
            scenario_version=result.scenario_version,
            result=result.model_dump(mode="json"),
        ))
        session.commit()


def get_simulation(simulation_id: str) -> dict[str, Any] | None:
    initialize_database()
    with SessionLocal() as session:
        record = session.get(SimulationRecord, simulation_id)
        return dict(record.result) if record else None
