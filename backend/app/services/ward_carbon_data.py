"""Read the precomputed, fractional-area 2021 ward traffic CO2 estimates."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[3]
ANNUAL_CSV_PATH = PROJECT_DIR / "data" / "processed" / "carbon" / "delhi_ward_co2_modelled_2021_annual.csv"
METHODOLOGY_PATH = PROJECT_DIR / "data" / "processed" / "carbon" / "CHETNA_Road_Delhi_CO2_methodology.md"

EXPECTED_WARD_COUNT = 272
ESTIMATE_LABEL = "MODELLED 2021 ROAD-TRAFFIC CO2"
REQUIRED_COLUMNS = {
    "estimate_label", "ward_id", "ward_name", "annual_co2_tonnes",
    "valid_area_coverage_pct", "coverage_flag", "contributing_grid_cells",
}
VALID_COVERAGE_FLAGS = {"ADEQUATE_GE90%", "PARTIAL_LT90%", "NO_COVERAGE"}


def _finite_number(value: str | None, *, minimum: float | None = None, maximum: float | None = None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    if not math.isfinite(number) or (minimum is not None and number < minimum):
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def load_annual_ward_carbon() -> dict[str, Any]:
    """Load and validate every row; malformed or duplicate IDs fail the request."""
    if not ANNUAL_CSV_PATH.is_file():
        raise ValueError(f"Annual ward carbon data file is missing: {ANNUAL_CSV_PATH.name}")
    if not METHODOLOGY_PATH.is_file():
        raise ValueError(f"Carbon methodology file is missing: {METHODOLOGY_PATH.name}")
    # Resolve/read both paths from the repository root regardless of process CWD.
    METHODOLOGY_PATH.read_text(encoding="utf-8")

    wards: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    with ANNUAL_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("Annual ward carbon CSV is missing required columns.")
        for row_number, row in enumerate(reader, start=2):
            raw_id = row.get("ward_id") or ""
            if not re.fullmatch(r"[0-9]+", raw_id.strip()):
                raise ValueError(f"Invalid ward_id on CSV row {row_number}.")
            ward_id = int(raw_id)
            if ward_id <= 0 or ward_id > EXPECTED_WARD_COUNT:
                raise ValueError(f"Invalid ward_id on CSV row {row_number}.")
            if ward_id in seen_ids:
                raise ValueError(f"Duplicate ward_id {ward_id} in annual ward carbon CSV.")
            seen_ids.add(ward_id)

            name = (row.get("ward_name") or "").strip()
            flag = (row.get("coverage_flag") or "").strip()
            if not name:
                raise ValueError(f"Missing ward_name on CSV row {row_number}.")
            if flag not in VALID_COVERAGE_FLAGS:
                raise ValueError(f"Invalid coverage_flag on CSV row {row_number}.")
            label = (row.get("estimate_label") or "").strip()
            if label != ESTIMATE_LABEL:
                raise ValueError(f"Unexpected estimate_label on CSV row {row_number}.")

            raw_cells = (row.get("contributing_grid_cells") or "").strip()
            if not re.fullmatch(r"[0-9]+", raw_cells):
                raise ValueError(f"Invalid contributing_grid_cells on CSV row {row_number}.")
            coverage = _finite_number(row.get("valid_area_coverage_pct"), minimum=0, maximum=100)
            wards.append({
                "ward_id": ward_id,
                "ward_name": name,
                # Missing, malformed, non-finite, or negative emissions remain unavailable.
                "annual_co2_tonnes": _finite_number(row.get("annual_co2_tonnes"), minimum=0),
                "valid_area_coverage_pct": coverage,
                "coverage_flag": flag,
                "contributing_grid_cells": int(raw_cells),
            })

    if len(wards) != EXPECTED_WARD_COUNT:
        raise ValueError(f"Expected {EXPECTED_WARD_COUNT} ward rows; found {len(wards)}.")

    return {
        "metadata": {
            "estimate_label": ESTIMATE_LABEL,
            "year": 2021,
            "unit": "tonnes CO2/year",
            "source_name": "CHETNA-Road Delhi road-traffic emissions dataset",
            "source_url": "https://doi.org/10.6084/m9.figshare.28330067.v2",
            "methodology_file": METHODOLOGY_PATH.name,
            "methodology_summary": (
                "Daily cell totals were allocated by fractional cell-polygon area overlap, assuming "
                "emissions are uniform within each cell. NaN cells were not imputed; partial wards "
                "cover only their valid grid area. Values are modelled historical road-traffic CO2, "
                "not measured, current, or all-sector emissions."
            ),
        },
        "wards": wards,
    }
