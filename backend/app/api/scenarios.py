from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from app.phase10.catalog import intervention_catalog
from app.phase10.graph import run_scenario_workflow
from app.phase10.repository import (
    get_scenario,
    list_scenarios,
    persist_scenario_set,
    persist_scenario_version,
)
from app.phase10.schemas import Scenario, ScenarioGenerationRequest, ScenarioSet, ScenarioVersionRequest
from app.phase11.engine import run_simulation
from app.phase11.schemas import SimulationInput, SimulationRequest
from app.phase9.graph.state import UrbanState

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenario-generation"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=ScenarioSet)
async def generate_scenarios(request: ScenarioGenerationRequest) -> ScenarioSet:
    try:
        scenario_set = run_scenario_workflow(request)
        persist_scenario_set(scenario_set)
        logger.info(
            "Persisted generated scenario set",
            extra={
                "request_id": scenario_set.request_id,
                "workflow_id": scenario_set.workflow_id,
                "scenario_count": len(scenario_set.scenarios),
            },
        )
        return scenario_set
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Could not persist generated scenarios")
        raise HTTPException(status_code=503, detail="Scenario storage is unavailable.") from exc
    except Exception as exc:
        logger.exception("Scenario generation failed")
        raise HTTPException(status_code=500, detail="Scenario generation failed.") from exc


@router.get("")
async def get_scenarios(
    city: str | None = None,
    zone: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    try:
        scenarios = list_scenarios(city=city, zone=zone, limit=limit, offset=offset)
        return {"count": len(scenarios), "limit": limit, "offset": offset, "scenarios": scenarios}
    except SQLAlchemyError as exc:
        logger.exception("Could not list scenarios")
        raise HTTPException(status_code=503, detail="Scenario storage is unavailable.") from exc


@router.post("/simulate")
async def simulate_scenario(request: dict[str, Any]) -> dict[str, Any]:
    scenario_data = request.get("scenario") or request
    if not isinstance(scenario_data, dict):
        raise HTTPException(status_code=422, detail="A scenario payload is required.")
    scenario = Scenario.model_validate(scenario_data)
    urban_state = request.get("urban_state") or {
        "workflow_id": "scenario-simulate",
        "request": {"query": f"Simulate {scenario.name}", "city": scenario.city, "zone": scenario.zone},
    }
    simulation_input = request.get("simulation_input") or {"baseline_metrics": {}}
    try:
        result = run_simulation(
            SimulationRequest(
                urban_state=UrbanState.model_validate(urban_state),
                scenario=scenario,
                simulation_input=SimulationInput.model_validate(simulation_input),
            )
        )
        return result.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{scenario_id}")
async def get_scenario_by_id(
    scenario_id: str,
    version: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    try:
        scenario = get_scenario(scenario_id, version)
    except SQLAlchemyError as exc:
        logger.exception("Could not retrieve scenario", extra={"scenario_id": scenario_id})
        raise HTTPException(status_code=503, detail="Scenario storage is unavailable.") from exc
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    return scenario


@router.post("/{scenario_id}/versions", response_model=Scenario)
async def create_scenario_version(
    scenario_id: str,
    request: ScenarioVersionRequest,
) -> Scenario:
    try:
        previous_data = get_scenario(scenario_id)
    except SQLAlchemyError as exc:
        logger.exception("Could not retrieve scenario for versioning", extra={"scenario_id": scenario_id})
        raise HTTPException(status_code=503, detail="Scenario storage is unavailable.") from exc
    if previous_data is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    previous = Scenario.model_validate(previous_data)
    if not previous.interventions:
        raise HTTPException(status_code=409, detail="Baseline scenarios do not have intervention parameters to version.")

    interventions = {item.intervention_id: item for item in previous.interventions}
    for intervention_id, updates in request.parameter_updates.items():
        existing = interventions.get(intervention_id)
        definition = intervention_catalog.get(intervention_id)
        if existing is None or definition is None:
            raise HTTPException(
                status_code=422,
                detail=f"Intervention '{intervention_id}' is not part of this scenario.",
            )
        allowed = set(definition.required_parameters + definition.optional_parameters)
        unknown = set(updates) - allowed
        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported parameters for {definition.name}: {', '.join(sorted(unknown))}.",
            )
        parameters = {**existing.parameters, **updates}
        missing = set(definition.required_parameters) - set(parameters)
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Required parameters are missing for {definition.name}: {', '.join(sorted(missing))}.",
            )
        for key, value in parameters.items():
            if value is None or isinstance(value, bool):
                raise HTTPException(status_code=422, detail=f"Parameter '{key}' must have a value.")
            if isinstance(value, (int, float)) and value <= 0:
                raise HTTPException(status_code=422, detail=f"Parameter '{key}' must be greater than zero.")
            if key in {"number_of_buses", "building_count", "tree_density"} and not isinstance(value, int):
                raise HTTPException(status_code=422, detail=f"Parameter '{key}' must be an integer.")
            if isinstance(value, str) and not value.strip():
                raise HTTPException(status_code=422, detail=f"Parameter '{key}' must not be empty.")
            if isinstance(value, list) and not value:
                raise HTTPException(status_code=422, detail=f"Parameter '{key}' must not be an empty list.")
        limits = previous.constraint_values
        area = parameters.get("area_hectares", parameters.get("land_required_hectares"))
        if (
            limits.available_land_hectares is not None
            and isinstance(area, (int, float))
            and area > limits.available_land_hectares
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Required land exceeds available land ({limits.available_land_hectares} hectares).",
            )
        duration = next(
            (
                parameters[key]
                for key in ("implementation_period_years", "deployment_period_years")
                if key in parameters
            ),
            None,
        )
        if (
            limits.time_horizon_years is not None
            and isinstance(duration, (int, float))
            and duration > limits.time_horizon_years
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Implementation duration exceeds the planning horizon ({limits.time_horizon_years} years).",
            )
        interventions[intervention_id] = existing.model_copy(update={
            "parameters": parameters,
            "parameter_sources": {
                **existing.parameter_sources,
                **{key: "user_input" for key in updates},
            },
        })

    next_version = previous.model_copy(deep=True)
    next_version.scenario_version += 1
    next_version.interventions = list(interventions.values())
    next_version.implementation_parameters = {
        item.intervention_id: item.parameters for item in next_version.interventions
    }
    next_version.scale = {
        item.intervention_id: item.parameters for item in next_version.interventions
    }
    next_version.status = "REQUIRES_REVIEW"
    next_version.constraints = list(dict.fromkeys(
        next_version.constraints + ["Parameters changed; feasibility and policy review are required."]
    ))
    next_version.provenance = {
        **next_version.provenance,
        "supersedes_version": previous.scenario_version,
    }
    try:
        persist_scenario_version(previous_data["request_id"], next_version)
    except SQLAlchemyError as exc:
        logger.exception(
            "Could not persist scenario version",
            extra={"scenario_id": scenario_id, "scenario_version": next_version.scenario_version},
        )
        raise HTTPException(status_code=503, detail="Scenario storage is unavailable.") from exc
    return next_version
