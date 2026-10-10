from fastapi import APIRouter

from .auth import router as auth_router
from .carbon import router as carbon_router
from .agentic import router as agentic_router
from .digital_twin import router as digital_twin_router
from .federated import router as federated_router
from .predictions import router as prediction_router
from .rag import router as rag_router
from .scenarios import router as scenarios_router
from .system import router as system_router
from .urban_memory import router as urban_memory_router
from app.phase11.api import router as simulation_router
from app.phase12.api import router as optimization_router
from app.phase13.api import explanation_router, router as explainability_router
from app.phase13.pipeline_api import router as pipeline_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(prediction_router)
router.include_router(carbon_router)
router.include_router(digital_twin_router)
router.include_router(urban_memory_router)
router.include_router(rag_router)
router.include_router(federated_router)
router.include_router(agentic_router)
router.include_router(scenarios_router)
router.include_router(simulation_router)
router.include_router(optimization_router)
router.include_router(explainability_router)
router.include_router(explanation_router)
router.include_router(pipeline_router)
router.include_router(system_router)

__all__ = ["router"]
