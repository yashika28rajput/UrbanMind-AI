from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MemoryType = Literal[
    "policy",
    "simulation",
    "environment",
    "recommendation",
    "intervention",
    "decision_log",
]
MemoryOutcome = Literal["success", "failure", "ongoing", "unknown"]


class UrbanMemoryCreate(BaseModel):
    memory_type: MemoryType
    city: str = Field(min_length=1, max_length=120)
    zone: str | None = Field(default=None, max_length=160)
    title: str = Field(min_length=1, max_length=250)
    content: str = Field(min_length=1, max_length=20000)
    structured_data: dict[str, Any] = Field(default_factory=dict)
    outcome: MemoryOutcome | None = None
    source_ref: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")


class UrbanMemorySearch(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    memory_type: MemoryType | None = None
    city: str | None = Field(default=None, max_length=120)
    zone: str | None = Field(default=None, max_length=160)
    outcome: MemoryOutcome | None = None
    limit: int = Field(default=10, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")


class UrbanMemoryOutcomeUpdate(BaseModel):
    outcome: MemoryOutcome
    outcome_notes: str | None = Field(default=None, max_length=5000)

    model_config = ConfigDict(extra="forbid")
