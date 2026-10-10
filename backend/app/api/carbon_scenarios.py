import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.phase10.repository import persist_scenario_set
from app.phase10.schemas import Scenario, ScenarioSet
from app.schemas.carbon_scenario import CarbonScenarioRequest, CarbonScenarioResult
from app.services.carbon_scenario_service import calculate_transport_carbon_scenario

router = APIRouter(prefix="/api/v1/carbon", tags=["carbon-scenarios"])
logger = logging.getLogger(__name__)


@router.post("/scenarios/calculate", response_model=CarbonScenarioResult)
async def calculate_carbon_scenario(request: CarbonScenarioRequest) -> CarbonScenarioResult:
    try:
        result = calculate_transport_carbon_scenario(request)
        scenario = Scenario(
            name=request.scenario_name,
            description="User-entered diesel baseline versus electric transport scenario; see saved assumptions and calculation provenance.",
            city="Delhi",
            intervention_type="transport_carbon_comparison",
            implementation_parameters={"carbon_scenario_inputs": request.model_dump(mode="json")},
            carbon_reduction_availability_reason=(
                "This standalone transport calculation is not a calibrated city or ward carbon metric."
            ),
            assumptions=[result.assumptions.service_boundary, result.assumptions.period_basis],
            status="SIMULATED" if result.result_classification == "SIMULATED" else "DRAFT",
            provenance={},
        )
        result = result.model_copy(update={"scenario_id": scenario.scenario_id})
        scenario.provenance = {"carbon_scenario_result": result.model_dump(mode="json")}
        scenario_set = ScenarioSet(
            city="Delhi",
            problem_statement=f"Carbon scenario calculation: {request.scenario_name}",
            generation_method="user_input_carbon_calculation",
            scenarios=[scenario],
        )
        persist_scenario_set(scenario_set)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("Could not persist carbon scenario")
        raise HTTPException(status_code=503, detail="Carbon scenario storage is unavailable.") from exc
