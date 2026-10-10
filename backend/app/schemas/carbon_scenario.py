from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CarbonFactorProvenance(BaseModel):
    source: str = Field(min_length=1, max_length=300)
    version: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=1000)
    status: Literal["Illustrative", "Unverified", "Verified"]

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CarbonScenarioRequest(BaseModel):
    scenario_name: str = Field(min_length=1, max_length=120)
    annual_vehicle_km: float = Field(gt=0, allow_inf_nan=False)
    diesel_litres_per_vehicle_km: float = Field(gt=0, allow_inf_nan=False)
    electric_kwh_per_vehicle_km: float = Field(gt=0, allow_inf_nan=False)
    diesel_emission_factor_kg_co2_per_litre: float = Field(gt=0, allow_inf_nan=False)
    electricity_emission_factor_kg_co2_per_kwh: float = Field(gt=0, allow_inf_nan=False)
    baseline_period_start: date
    baseline_period_end: date
    project_period_start: date
    project_period_end: date
    activity_source: str = Field(min_length=1, max_length=300)
    activity_reference: str = Field(min_length=1, max_length=1000)
    input_classification: Literal["Illustrative", "Estimated", "Measured"]
    diesel_factor: CarbonFactorProvenance
    electricity_factor: CarbonFactorProvenance

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_evidence_and_periods(self) -> "CarbonScenarioRequest":
        for label, start, end in (
            ("Baseline", self.baseline_period_start, self.baseline_period_end),
            ("Project", self.project_period_start, self.project_period_end),
        ):
            duration_days = (end - start).days
            if duration_days not in (364, 365):
                raise ValueError(
                    f"{label} reporting period must cover one annual reporting period "
                    "(365 or 366 inclusive days)."
                )
        if self.baseline_period_end >= self.project_period_start:
            raise ValueError("Baseline reporting period must end before the project reporting period starts.")

        if self.input_classification != "Illustrative":
            if "illustrative demonstration" in self.activity_source.lower():
                raise ValueError(
                    "Replace the illustrative activity source and reference before "
                    "classifying this scenario as Estimated or Measured."
                )
            if "illustrative demonstration" in self.activity_reference.lower():
                raise ValueError(
                    "Replace the illustrative activity source and reference before "
                    "classifying this scenario as Estimated or Measured."
                )
            if self.diesel_factor.status == "Illustrative" or self.electricity_factor.status == "Illustrative":
                raise ValueError(
                    "Replace illustrative emission factors before classifying this scenario "
                    "as Estimated or Measured."
                )

        if self.input_classification == "Measured":
            if self.diesel_factor.status != "Verified" or self.electricity_factor.status != "Verified":
                raise ValueError("Measured scenarios require verified provenance for both emission factors.")
            if not self.diesel_factor.reference.strip() or not self.electricity_factor.reference.strip():
                raise ValueError("Measured scenarios require references for both verified emission factors.")

        return self


class CarbonScenarioFactorProvenance(BaseModel):
    source: str
    version: str
    reference: str
    status: Literal["Illustrative", "Unverified", "Verified"]


class CarbonScenarioDieselFactorAssumption(CarbonScenarioFactorProvenance):
    value_kg_co2_per_litre: float = Field(allow_inf_nan=False)


class CarbonScenarioElectricityFactorAssumption(CarbonScenarioFactorProvenance):
    value_kg_co2_per_kwh: float = Field(allow_inf_nan=False)


class CarbonScenarioPeriods(BaseModel):
    baseline_start: date
    baseline_end: date
    project_start: date
    project_end: date


class CarbonScenarioAssumptions(BaseModel):
    service_boundary: str
    period_basis: str
    calculation: str
    activity_source: str
    activity_reference: str
    input_classification: Literal["Illustrative", "Estimated", "Measured"]
    diesel_factor: CarbonScenarioDieselFactorAssumption
    electricity_factor: CarbonScenarioElectricityFactorAssumption


class CarbonScenarioResult(BaseModel):
    scenario_id: str | None = None
    scenario_name: str
    result_classification: Literal["SIMULATED", "ESTIMATED", "MEASURED"]
    display_label: str
    unit: Literal["tCO2/year"]
    baseline_emissions_tco2_per_year: float = Field(allow_inf_nan=False)
    project_emissions_tco2_per_year: float = Field(allow_inf_nan=False)
    avoided_emissions_tco2_per_year: float = Field(allow_inf_nan=False)
    percentage_change: float | None = Field(default=None, allow_inf_nan=False)
    baseline_diesel_litres_per_year: float = Field(allow_inf_nan=False)
    project_electricity_kwh_per_year: float = Field(allow_inf_nan=False)
    annual_vehicle_km: float = Field(allow_inf_nan=False)
    periods: CarbonScenarioPeriods
    assumptions: CarbonScenarioAssumptions
