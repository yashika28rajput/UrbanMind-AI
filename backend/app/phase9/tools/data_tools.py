from __future__ import annotations

from app.phase9.schemas import DataStatus


def validate_data(city: str, zone: str, requested_interventions: list[str] | None = None) -> DataStatus:
    missing: list[str] = []
    if not city.strip():
        missing.append("city")
    if not zone.strip():
        missing.append("zone")
    if not requested_interventions:
        missing.append("requested_interventions")

    return DataStatus(
        data_available=not missing,
        missing_datasets=missing,
        data_quality="good" if not missing else "partial",
        freshness="current",
        coverage="city-level",
        warnings=["Synthetic validation used for deterministic phase-9 workflow."] if not missing else ["Missing inputs flagged for review."],
    )
