import math

from app.schemas.carbon_scenario import CarbonScenarioRequest, CarbonScenarioResult


def calculate_transport_carbon_scenario(request: CarbonScenarioRequest) -> CarbonScenarioResult:
    """Compare diesel baseline and electric project emissions for equal annual service."""
    baseline_fuel_litres = request.annual_vehicle_km * request.diesel_litres_per_vehicle_km
    baseline_kg_co2 = baseline_fuel_litres * request.diesel_emission_factor_kg_co2_per_litre
    project_electricity_kwh = request.annual_vehicle_km * request.electric_kwh_per_vehicle_km
    project_kg_co2 = (
        project_electricity_kwh * request.electricity_emission_factor_kg_co2_per_kwh
    )
    baseline_tonnes = baseline_kg_co2 / 1000
    project_tonnes = project_kg_co2 / 1000
    avoided_tonnes = baseline_tonnes - project_tonnes
    percentage_change = (
        (project_tonnes - baseline_tonnes) / baseline_tonnes * 100
        if baseline_tonnes != 0
        else None
    )
    calculated_values = (
        baseline_fuel_litres,
        baseline_kg_co2,
        project_electricity_kwh,
        project_kg_co2,
        baseline_tonnes,
        project_tonnes,
        avoided_tonnes,
    )
    if any(not math.isfinite(value) for value in calculated_values) or (
        percentage_change is not None and not math.isfinite(percentage_change)
    ):
        raise ValueError("Inputs produce a non-finite result; reduce the activity, intensities, or factors.")

    classification = {
        "Illustrative": "SIMULATED",
        "Estimated": "ESTIMATED",
        "Measured": "MEASURED",
    }[request.input_classification]

    result = {
        "scenario_name": request.scenario_name,
        "result_classification": classification,
        "display_label": (
            "SIMULATED SCENARIO — NOT MEASURED"
            if classification == "SIMULATED"
            else f"{classification} SCENARIO"
        ),
        "unit": "tCO2/year",
        "baseline_emissions_tco2_per_year": baseline_tonnes,
        "project_emissions_tco2_per_year": project_tonnes,
        "avoided_emissions_tco2_per_year": avoided_tonnes,
        "percentage_change": percentage_change,
        "baseline_diesel_litres_per_year": baseline_fuel_litres,
        "project_electricity_kwh_per_year": project_electricity_kwh,
        "annual_vehicle_km": request.annual_vehicle_km,
        "periods": {
            "baseline_start": request.baseline_period_start.isoformat(),
            "baseline_end": request.baseline_period_end.isoformat(),
            "project_start": request.project_period_start.isoformat(),
            "project_end": request.project_period_end.isoformat(),
        },
        "assumptions": {
            "service_boundary": "The same annual vehicle-kilometres are provided by diesel in the baseline and electricity in the project case.",
            "period_basis": "Annual vehicle-kilometres and annual emissions; each declared reporting period covers one year.",
            "calculation": "Baseline: annual vehicle-km × diesel L/vehicle-km × diesel kg CO2/L ÷ 1,000. Project: annual vehicle-km × electric kWh/vehicle-km × electricity kg CO2/kWh ÷ 1,000.",
            "activity_source": request.activity_source,
            "activity_reference": request.activity_reference,
            "input_classification": request.input_classification,
            "diesel_factor": {
                "value_kg_co2_per_litre": request.diesel_emission_factor_kg_co2_per_litre,
                "source": request.diesel_factor.source,
                "version": request.diesel_factor.version,
                "reference": request.diesel_factor.reference,
                "status": request.diesel_factor.status,
            },
            "electricity_factor": {
                "value_kg_co2_per_kwh": request.electricity_emission_factor_kg_co2_per_kwh,
                "source": request.electricity_factor.source,
                "version": request.electricity_factor.version,
                "reference": request.electricity_factor.reference,
                "status": request.electricity_factor.status,
            },
        },
    }
    return CarbonScenarioResult.model_validate(result)
