from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EnvironmentalMetric = Literal[
    "aqi",
    "pm25",
    "pm10",
    "no2",
    "o3",
    "co",
    "so2",
    "temperature",
    "land_surface_temperature",
    "green_cover",
    "population",
]
DataClassification = Literal["observed", "official", "derived", "estimated", "illustrative"]

METRIC_UNITS: dict[str, set[str]] = {
    "aqi": {"AQI"},
    "pm25": {"µg/m³", "mg/m³"},
    "pm10": {"µg/m³", "mg/m³"},
    "no2": {"µg/m³", "mg/m³", "ppb"},
    "o3": {"µg/m³", "mg/m³", "ppb"},
    "co": {"µg/m³", "mg/m³", "ppb"},
    "so2": {"µg/m³", "mg/m³", "ppb"},
    "temperature": {"°C"},
    "land_surface_temperature": {"°C"},
    "green_cover": {"%"},
    "population": {"people"},
}


class EnvironmentalRecordInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ward_id: int = Field(gt=0)
    observation_date: date
    metric: EnvironmentalMetric
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=32)
    data_classification: DataClassification
    source_name: str = Field(min_length=1, max_length=300)
    source_reference: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        cleaned = value.replace("μ", "µ").strip()
        aliases = {
            "ug/m3": "µg/m³",
            "µg/m3": "µg/m³",
            "mg/m3": "mg/m³",
            "degc": "°C",
            "c": "°C",
            "percent": "%",
            "person": "people",
            "persons": "people",
        }
        key = cleaned.casefold().replace(" ", "").replace("³", "3")
        return aliases.get(key, cleaned)

    @model_validator(mode="after")
    def validate_metric_unit_and_range(self) -> "EnvironmentalRecordInput":
        if self.unit not in METRIC_UNITS[self.metric]:
            raise ValueError(f"Unit '{self.unit}' is not supported for metric '{self.metric}'.")
        if self.value < 0 and self.metric not in {"temperature", "land_surface_temperature"}:
            raise ValueError(f"Metric '{self.metric}' must not be negative.")
        if self.metric == "aqi" and self.value > 500:
            raise ValueError("AQI must be between 0 and 500.")
        if self.metric in {"temperature", "land_surface_temperature"} and not -90 <= self.value <= 80:
            raise ValueError(f"Metric '{self.metric}' must be between -90 and 80 °C.")
        if self.metric == "green_cover" and self.value > 100:
            raise ValueError("Green cover must be between 0 and 100 percent.")
        if self.metric == "population" and not self.value.is_integer():
            raise ValueError("Population must be a whole number of people.")
        return self


class EnvironmentalRecord(EnvironmentalRecordInput):
    record_id: str = Field(default_factory=lambda: f"ENV-{uuid4().hex[:16].upper()}")
    source_reference: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EnvironmentalRecordPage(BaseModel):
    records: list[EnvironmentalRecord]
    total: int
    limit: int
    offset: int


class UploadPreview(BaseModel):
    filename: str
    checksum: str
    columns: list[str]
    preview_rows: list[dict[str, str | None]]
    total_rows_read: int


class ValidationIssue(BaseModel):
    row_number: int
    field: str
    reason: str
    kind: Literal["invalid", "duplicate"] = "invalid"


class ImportValidationReport(BaseModel):
    filename: str
    checksum: str
    total_rows_read: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    errors: list[ValidationIssue]


class EnvironmentalImportResult(ImportValidationReport):
    import_id: str
    imported_at: datetime
    rows_inserted: int
    rows_skipped: int
    idempotent_retry: bool = False