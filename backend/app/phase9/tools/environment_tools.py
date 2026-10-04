from __future__ import annotations

from app.phase9.schemas import EnvironmentResult


def simulate_environmental_impact(city: str, zone: str, interventions: list[str]) -> EnvironmentResult:
    air_quality = "strong improvement" if any(item.lower().startswith("green") for item in interventions) else "moderate improvement"
    return EnvironmentResult(
        air_quality_impact=air_quality,
        heat_impact="moderate cooling",
        green_cover_impact="positive",
        carbon_impact="moderate reduction",
        environmental_risks=["Implementation gap risk if maintenance is not funded."],
        assumptions=[f"Scenario evaluated for {city} ? {zone} using mock environmental simulation."],
        evidence_ids=["env-sim-01"],
    )
