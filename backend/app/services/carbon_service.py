"""Activity-based carbon accounting.

    Emissions          = Activity quantity x Emission factor
    Carbon reduction   = Baseline emissions - Projected emissions

The service never supplies emission factors itself. Every activity must carry
an explicit factor *and* a non-empty citation for it, so no number can be
produced without a traceable input.
"""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PERIODS_PER_YEAR: dict[str, int] = {"day": 365, "month": 12, "year": 1}


class Activity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(ge=0, allow_inf_nan=False, description="Activity amount per `period`.")
    quantity_unit: str = Field(min_length=1, max_length=40, description="e.g. 'kWh', 'litre', 'km'.")
    period: Literal["day", "month", "year"] = "year"
    emission_factor_kgco2e_per_unit: float = Field(
        ge=0, allow_inf_nan=False, description="kg CO2e per one `quantity_unit`."
    )
    factor_source: str = Field(
        min_length=3, max_length=300, description="Citation for the emission factor (publisher, table, year)."
    )

    @field_validator("name", "quantity_unit", "factor_source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class CarbonCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline: list[Activity] = Field(min_length=1, max_length=200)
    projected: list[Activity] = Field(min_length=1, max_length=200)


class LineItem(BaseModel):
    name: str
    quantity_unit: str
    annual_quantity: float
    emission_factor_kgco2e_per_unit: float
    factor_source: str
    annual_emissions_kgco2e: float


def _line_items(activities: list[Activity]) -> list[LineItem]:
    items = []
    for item in activities:
        annual_quantity = item.quantity * PERIODS_PER_YEAR[item.period]
        annual_emissions = annual_quantity * item.emission_factor_kgco2e_per_unit
        if not math.isfinite(annual_quantity) or not math.isfinite(annual_emissions):
            raise ValueError("Inputs produce non-finite annual emissions; reduce the activity quantity or factor.")
        items.append(LineItem(
            name=item.name,
            quantity_unit=item.quantity_unit,
            annual_quantity=annual_quantity,
            emission_factor_kgco2e_per_unit=item.emission_factor_kgco2e_per_unit,
            factor_source=item.factor_source,
            annual_emissions_kgco2e=annual_emissions,
        ))
    return items


def _unit_by_name(activities: list[Activity]) -> dict[str, str]:
    units: dict[str, set[str]] = defaultdict(set)
    for item in activities:
        units[item.name.casefold()].add(item.quantity_unit)
    return {name: ", ".join(sorted(found)) for name, found in units.items()}


def calculate_carbon_reduction(request: CarbonCalculationRequest) -> dict[str, object]:
    # Baseline and projected activities with the same name must use the same unit,
    # otherwise the two totals are not comparable.
    baseline_units = _unit_by_name(request.baseline)
    projected_units = _unit_by_name(request.projected)
    for name in baseline_units.keys() & projected_units.keys():
        if baseline_units[name] != projected_units[name]:
            raise ValueError(
                f"Activity '{name}' uses different units in baseline ({baseline_units[name]}) "
                f"and projected ({projected_units[name]}); the totals would not be comparable."
            )
    for side, units in (("baseline", baseline_units), ("projected", projected_units)):
        if any("," in unit for unit in units.values()):
            raise ValueError(f"An activity name in {side} is used with more than one unit.")

    baseline_items = _line_items(request.baseline)
    projected_items = _line_items(request.projected)
    baseline_total = sum(item.annual_emissions_kgco2e for item in baseline_items)
    projected_total = sum(item.annual_emissions_kgco2e for item in projected_items)
    reduction = baseline_total - projected_total
    if not all(math.isfinite(value) for value in (baseline_total, projected_total, reduction)):
        raise ValueError("Inputs produce non-finite annual emissions; reduce the activity quantity or factor.")

    if baseline_total > 0:
        reduction_percent: float | None = round(reduction / baseline_total * 100.0, 2)
        percent_note = None
    else:
        reduction_percent = None
        percent_note = "Baseline emissions are zero, so a percentage reduction is undefined."
    if reduction_percent is not None and not math.isfinite(reduction_percent):
        raise ValueError("Inputs produce a non-finite percentage; reduce the activity quantity or factor.")

    warnings = [
        "Emission factors and activity quantities are user-supplied; this result is only as "
        "reliable as those inputs and is not a measured environmental outcome."
    ]
    only_baseline = sorted(baseline_units.keys() - projected_units.keys())
    only_projected = sorted(projected_units.keys() - baseline_units.keys())
    if only_baseline or only_projected:
        warnings.append(
            "Activities present on only one side are included in that side's total: "
            f"baseline only={only_baseline or 'none'}, projected only={only_projected or 'none'}."
        )

    return {
        "status": "calculated",
        "method": "activity_quantity_x_emission_factor",
        "evidence_type": "user_supplied_inputs",
        "unit": "kgCO2e/year",
        "baseline_emissions_kgco2e_per_year": round(baseline_total, 4),
        "projected_emissions_kgco2e_per_year": round(projected_total, 4),
        "reduction_kgco2e_per_year": round(reduction, 4),
        "reduction_percent": reduction_percent,
        "reduction_percent_note": percent_note,
        "direction": "reduction" if reduction > 0 else "increase" if reduction < 0 else "no_change",
        "baseline_line_items": [item.model_dump() for item in baseline_items],
        "projected_line_items": [item.model_dump() for item in projected_items],
        "warnings": warnings,
    }
