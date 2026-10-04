import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import CheckConstraint, DateTime, Index, JSON, String, Text, create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
load_dotenv(BACKEND_DIR / ".env", override=False)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{(Path(__file__).resolve().parent / 'urban_memory.sqlite3').as_posix()}"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UrbanMemory(Base):
    __tablename__ = "urban_memories"
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('policy', 'simulation', 'environment', 'recommendation', 'intervention', 'decision_log')",
            name="ck_urban_memories_type",
        ),
        CheckConstraint(
            "outcome IS NULL OR outcome IN ('success', 'failure', 'ongoing', 'unknown')",
            name="ck_urban_memories_outcome",
        ),
        Index("ix_urban_memories_city_zone_created", "city", "zone", "created_at"),
        Index("ix_urban_memories_type_created", "memory_type", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    zone: Mapped[str | None] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    outcome: Mapped[str | None] = mapped_column(String(16))
    source_ref: Mapped[str | None] = mapped_column(String(500), unique=True)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


@event.listens_for(engine, "connect")
def _configure_sqlite(connection: Any, _record: Any) -> None:
    if engine.dialect.name == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def initialize_database() -> None:
    Base.metadata.create_all(engine)


def insert_memory(values: dict[str, Any]) -> tuple[UrbanMemory, bool]:
    initialize_database()
    with SessionLocal() as session:
        source_ref = values.get("source_ref")
        if source_ref:
            existing = session.query(UrbanMemory).filter_by(source_ref=source_ref).one_or_none()
            if existing is not None:
                return existing, False

        memory = UrbanMemory(**values)
        session.add(memory)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            if source_ref:
                existing = session.query(UrbanMemory).filter_by(source_ref=source_ref).one_or_none()
                if existing is not None:
                    return existing, False
            raise ValueError("A memory with this source reference already exists.") from exc
        session.refresh(memory)
        return memory, True


def fetch_memory(memory_id: str) -> UrbanMemory | None:
    initialize_database()
    with SessionLocal() as session:
        return session.get(UrbanMemory, memory_id)


def update_memory_outcome(
    memory_id: str,
    *,
    outcome: str,
    content: str,
    structured_data: dict[str, Any],
    embedding: list[float],
    embedding_provider: str,
) -> UrbanMemory | None:
    initialize_database()
    with SessionLocal() as session:
        memory = session.get(UrbanMemory, memory_id)
        if memory is None:
            return None
        memory.outcome = outcome
        memory.content = content
        memory.structured_data = structured_data
        memory.embedding = embedding
        memory.embedding_provider = embedding_provider
        session.commit()
        session.refresh(memory)
        return memory


def fetch_memories(
    *,
    memory_type: str | None = None,
    city: str | None = None,
    zone: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[UrbanMemory]:
    initialize_database()
    with SessionLocal() as session:
        query = session.query(UrbanMemory)
        if memory_type:
            query = query.filter(UrbanMemory.memory_type == memory_type)
        if city:
            query = query.filter(UrbanMemory.city.ilike(city))
        if zone:
            query = query.filter(UrbanMemory.zone.ilike(zone))
        return (
            query.order_by(UrbanMemory.created_at.desc(), UrbanMemory.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )


def count_memories() -> int:
    initialize_database()
    with SessionLocal() as session:
        return session.query(UrbanMemory).count()


def get_database_backend() -> str:
    return engine.dialect.name
