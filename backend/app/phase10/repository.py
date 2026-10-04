from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.urban_memory_store import Base, SessionLocal, initialize_database
from app.phase10.schemas import Scenario, ScenarioSet


class ScenarioRequestRecord(Base):
    __tablename__ = "scenario_requests"

    request_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    workflow_id: Mapped[str | None] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(160))
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    scenario_set: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class ScenarioRecord(Base):
    __tablename__ = "scenarios"
    __table_args__ = (Index("ix_scenarios_city_zone", "city", "zone"),)

    scenario_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("scenario_requests.request_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


def persist_scenario_set(scenario_set: ScenarioSet) -> None:
    initialize_database()
    request_record = ScenarioRequestRecord(
        request_id=scenario_set.request_id,
        workflow_id=scenario_set.workflow_id,
        city=scenario_set.city,
        zone=scenario_set.zone,
        problem_statement=scenario_set.problem_statement,
        status=scenario_set.status,
        scenario_set=scenario_set.model_dump(mode="json"),
    )
    scenario_records = [
        ScenarioRecord(
            scenario_id=item.scenario_id,
            request_id=scenario_set.request_id,
            scenario_version=item.scenario_version,
            city=item.city,
            zone=item.zone,
            name=item.name,
            status=item.status,
            scenario_data=item.model_dump(mode="json"),
        )
        for item in scenario_set.scenarios
    ]
    with SessionLocal() as session, session.begin():
        session.add(request_record)
        session.flush()
        session.add_all(scenario_records)


def get_scenario(scenario_id: str, version: int | None = None) -> dict[str, Any] | None:
    initialize_database()
    with SessionLocal() as session:
        query = session.query(ScenarioRecord).filter(ScenarioRecord.scenario_id == scenario_id)
        if version is not None:
            query = query.filter(ScenarioRecord.scenario_version == version)
        else:
            query = query.order_by(ScenarioRecord.scenario_version.desc())
        record = query.first()
        if record is None:
            return None
        return {
            "request_id": record.request_id,
            "scenario_version": record.scenario_version,
            **record.scenario_data,
        }


def persist_scenario_version(request_id: str, scenario: Scenario) -> None:
    initialize_database()
    with SessionLocal() as session:
        session.add(ScenarioRecord(
            scenario_id=scenario.scenario_id,
            request_id=request_id,
            scenario_version=scenario.scenario_version,
            city=scenario.city,
            zone=scenario.zone,
            name=scenario.name,
            status=scenario.status,
            scenario_data=scenario.model_dump(mode="json"),
        ))
        session.commit()


def list_scenarios(
    *,
    city: str | None = None,
    zone: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    initialize_database()
    with SessionLocal() as session:
        query = session.query(ScenarioRecord)
        if city:
            query = query.filter(ScenarioRecord.city.ilike(city))
        if zone:
            query = query.filter(ScenarioRecord.zone.ilike(zone))
        rows = (
            query.order_by(ScenarioRecord.created_at.desc(), ScenarioRecord.scenario_id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [
            {
                "request_id": row.request_id,
                "scenario_version": row.scenario_version,
                **row.scenario_data,
            }
            for row in rows
        ]
