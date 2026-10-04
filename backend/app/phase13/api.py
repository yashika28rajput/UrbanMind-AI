from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.phase13.engine import explain_prediction, explain_recommendation, run_counterfactual
from app.phase13.schemas import (
    CounterfactualRequest,
    CounterfactualResult,
    ExplanationRequest,
    ExplanationResult,
    RecommendationExplanationRequest,
    RecommendationExplanationResult,
)

router = APIRouter(prefix="/api/v1/explain", tags=["explainability"])
explanation_router = APIRouter(prefix="/api/v1/explanation", tags=["explainability"])


@router.post("/prediction", response_model=ExplanationResult)
async def explain_prediction_endpoint(request: ExplanationRequest) -> ExplanationResult:
    try:
        return explain_prediction(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@explanation_router.post("/prediction", response_model=ExplanationResult)
async def explain_prediction_alias(request: ExplanationRequest) -> ExplanationResult:
    return await explain_prediction_endpoint(request)


@router.post("/recommendation", response_model=RecommendationExplanationResult)
async def explain_recommendation_endpoint(
    request: RecommendationExplanationRequest,
) -> RecommendationExplanationResult:
    try:
        return explain_recommendation(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@explanation_router.post("/recommendation", response_model=RecommendationExplanationResult)
async def explain_recommendation_alias(
    request: RecommendationExplanationRequest,
) -> RecommendationExplanationResult:
    return await explain_recommendation_endpoint(request)


@router.post("/counterfactual", response_model=CounterfactualResult)
async def counterfactual_endpoint(request: CounterfactualRequest) -> CounterfactualResult:
    try:
        return run_counterfactual(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@explanation_router.post("/counterfactual", response_model=CounterfactualResult)
async def counterfactual_alias(request: CounterfactualRequest) -> CounterfactualResult:
    return await counterfactual_endpoint(request)
