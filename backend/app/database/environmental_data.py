from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.urban_memory_store import Base


class EnvironmentalImport(Base):
    __tablename__ = "environmental_imports"
    __table_args__ = (UniqueConstraint("checksum", "mapping_digest", name="uq_environmental_import_source"),)

    import_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_rows_read: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_inserted: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_skipped: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class EnvironmentalObservation(Base):
    __tablename__ = "environmental_observations"
    __table_args__ = (
        UniqueConstraint(
            "ward_id", "observation_date", "metric", "source_name", "source_reference",
            name="uq_environmental_observation_source",
        ),
        UniqueConstraint("source_import_id", "source_row_number", name="uq_environmental_import_row"),
        Index("ix_environmental_observations_ward_date", "ward_id", "observation_date"),
        Index("ix_environmental_observations_metric_date", "metric", "observation_date"),
    )

    record_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    ward_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    data_classification: Mapped[str] = mapped_column(String(16), nullable=False)
    source_name: Mapped[str] = mapped_column(String(300), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    notes: Mapped[str | None] = mapped_column(Text)
    source_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("environmental_imports.import_id", ondelete="RESTRICT")
    )
    source_row_number: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )