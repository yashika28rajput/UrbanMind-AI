from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd

from app.phase11.schemas import SimulationResult
from app.phase12.schemas import OptimizationResult
from app.phase13.schemas import (
    CounterfactualRequest,
    CounterfactualResult,
    ExplanationRequest,
    ExplanationResult,
    FeatureContribution,
    RecommendationExplanationRequest,
    RecommendationExplanationResult,
    StrategyExplanation,
)
from app.services import prediction_service

MODEL_CONFIG: dict[str, tuple[Path, Path, Callable[..., dict[str, Any]]]] = {
    "aqi": (
        prediction_service.AQI_MODEL_PATH,
        prediction_service.AQI_MODEL_INFO_PATH,
        prediction_service.predict_aqi,
    ),
    "urban_heat": (
        prediction_service.URBAN_HEAT_MODEL_PATH,
        prediction_service.URBAN_HEAT_MODEL_INFO_PATH,
        prediction_service.predict_urban_heat,
    ),
    "green_cover": (
        prediction_service.GREEN_COVER_MODEL_PATH,
        prediction_service.GREEN_COVER_MODEL_INFO_PATH,
        prediction_service.predict_green_cover,
    ),
    "carbon": (
        prediction_service.CARBON_REDUCTION_MODEL_PATH,
        prediction_service.CARBON_REDUCTION_MODEL_INFO_PATH,
        prediction_service.estimate_carbon_reduction,
    ),
    "health_risk": (
        prediction_service.HEALTH_RISK_MODEL_PATH,
        prediction_service.HEALTH_RISK_MODEL_INFO_PATH,
        prediction_service.predict_health_risk,
    ),
}


def _config_name(model_name: str) -> str:
    return "carbon" if model_name == "carbon_reduction" else model_name


@lru_cache(maxsize=16)
def _cached_asset_digest(
    model_path_text: str,
    info_path_text: str,
    model_mtime_ns: int,
    model_size: int,
    info_mtime_ns: int,
    info_size: int,
) -> str:
    digest = hashlib.sha256()
    for path_text in (model_path_text, info_path_text):
        with Path(path_text).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _asset_version(model_name: str, metadata: dict[str, Any]) -> str:
    model_path, info_path, _ = MODEL_CONFIG[_config_name(model_name)]
    model_stat, info_stat = model_path.stat(), info_path.stat()
    digest = _cached_asset_digest(
        str(model_path),
        str(info_path),
        model_stat.st_mtime_ns,
        model_stat.st_size,
        info_stat.st_mtime_ns,
        info_stat.st_size,
    )
    label = metadata.get(
        "version",
        metadata.get("selected_model", metadata.get("model_name", metadata.get("model", "unknown"))),
    )
    return f"{label} ({digest})"


def _load_model(model_name: str) -> tuple[Any, dict[str, Any], Callable[..., dict[str, Any]]]:
    model_path, info_path, predictor = MODEL_CONFIG[_config_name(model_name)]
    if not model_path.exists() or not info_path.exists():
        raise ValueError(f"The configured {model_name} model or its metadata is unavailable.")
    with info_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    model = joblib.load(model_path)
    return model, metadata, predictor


def _predict(predictor: Callable[..., dict[str, Any]], features: dict[str, float]) -> tuple[float, dict[str, Any]]:
    result = predictor(features)
    return float(result["predicted_value"]), result


def explain_prediction(request: ExplanationRequest) -> ExplanationResult:
    import shap

    model, metadata, predictor = _load_model(request.model_name)
    required = metadata.get("features", [])
    missing = sorted(set(required) - request.features.keys())
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    values = {name: float(request.features[name]) for name in required}
    prediction, prediction_result = _predict(predictor, values)
    frame = pd.DataFrame([values], columns=required)

    if request.model_name in {"aqi", "urban_heat"}:
        if not hasattr(model, "predict"):
            raise ValueError(f"The {request.model_name} model does not support model-specific Tree SHAP.")
        explainer = shap.TreeExplainer(model)
        raw_values = np.asarray(explainer.shap_values(frame))
        if raw_values.ndim == 2:
            contributions = raw_values[0]
        else:
            contributions = raw_values.reshape(-1)
        base_values = np.asarray(explainer.expected_value).reshape(-1)
        baseline_value = float(base_values[0]) if base_values.size else None
        method = "TreeExplainer"
    else:
        if not request.background_features:
            raise ValueError(
                f"background_features are required for model-agnostic SHAP on the {request.model_name} formula model."
            )
        background_rows = []
        for row in request.background_features:
            absent = sorted(set(required) - row.keys())
            if absent:
                raise ValueError(f"Background row is missing required features: {absent}")
            background_rows.append([float(row[name]) for name in required])
        background = np.asarray(background_rows, dtype=float)

        def predict_batch(batch: np.ndarray) -> np.ndarray:
            return np.asarray([
                _predict(predictor, dict(zip(required, row, strict=True)))[0]
                for row in np.asarray(batch)
            ])

        explainer = shap.PermutationExplainer(predict_batch, background, seed=0)
        explanation = explainer(frame, max_evals=max(2 * len(required) + 1, 10), silent=True)
        contributions = np.asarray(explanation.values)[0]
        baseline_value = float(np.asarray(explanation.base_values).reshape(-1)[0])
        method = "PermutationExplainer"

    feature_contributions = [
        FeatureContribution(
            feature=name,
            feature_value=values[name],
            shap_value=float(value),
            influence=(
                "raises_prediction" if value > 0 else "lowers_prediction" if value < 0 else "neutral"
            ),
        )
        for name, value in zip(required, contributions, strict=True)
    ]
    feature_contributions.sort(key=lambda item: abs(item.shap_value or 0.0), reverse=True)
    errors = metadata.get("test_metrics", metadata.get("validation_metrics", {}))
    uncertainty = {
        str(key): float(value)
        for key, value in errors.items()
        if isinstance(value, (int, float)) and key.lower() in {"mae", "rmse"}
    }
    version = _asset_version(request.model_name, metadata)
    return ExplanationResult(
        model_name=request.model_name,
        model_version=version,
        prediction=prediction,
        target=str(metadata.get("target", request.model_name)),
        unit=metadata.get("unit"),
        baseline_value=baseline_value,
        feature_contributions=feature_contributions,
        confidence=None,
        uncertainty=uncertainty,
        explanation_method=method,
    )


def _validate_and_predict(model_name: str, features: dict[str, float]) -> tuple[float, dict[str, Any], dict[str, Any]]:
    _, metadata, predictor = _load_model(model_name)
    required = metadata.get("features", [])
    missing = sorted(set(required) - features.keys())
    if missing:
        raise ValueError(f"Missing required features: {missing}")
    clean = {name: float(features[name]) for name in required}
    prediction, result = _predict(predictor, clean)
    return prediction, result, metadata


def run_counterfactual(request: CounterfactualRequest) -> CounterfactualResult:
    if request.feature_name not in request.features:
        raise ValueError(f"Feature '{request.feature_name}' must be present in features.")
    _, model_metadata, _ = _load_model(request.model_name)
    if request.feature_name not in model_metadata.get("features", []):
        raise ValueError(f"Feature '{request.feature_name}' is not used by the {request.model_name} model.")
    baseline_features = dict(request.features)
    counterfactual_features = dict(request.features)
    baseline_value = float(baseline_features[request.feature_name])
    counterfactual_features[request.feature_name] = request.counterfactual_value
    baseline, _, metadata = _validate_and_predict(request.model_name, baseline_features)
    counterfactual, _, _ = _validate_and_predict(request.model_name, counterfactual_features)
    return CounterfactualResult(
        model_name=request.model_name,
        model_version=_asset_version(request.model_name, metadata),
        feature_name=request.feature_name,
        baseline_feature_value=baseline_value,
        counterfactual_feature_value=request.counterfactual_value,
        baseline_prediction=baseline,
        counterfactual_prediction=counterfactual,
        absolute_delta=counterfactual - baseline,
        target=str(metadata.get("target", request.model_name)),
    )


def explain_recommendation(
    request: RecommendationExplanationRequest,
) -> RecommendationExplanationResult:
    simulations = {item.simulation_id: item for item in request.simulations}
    pareto = request.optimization_result.pareto_solutions
    preferred = next(
        (item for item in pareto if item.decision_score is not None),
        None,
    )
    reasons: list[str] = []
    tradeoffs: list[str] = []
    strategy_explanations: list[StrategyExplanation] = []
    limitations = [
        "The explanation is derived from supplied simulation metrics and Pareto objectives; it is not a causal claim."
    ]
    objective_directions = {
        item.name: item.direction for item in request.optimization_result.objectives
    }
    for solution in pareto:
        simulation = simulations.get(solution.simulation_id)
        if simulation is None:
            raise ValueError(f"Simulation '{solution.simulation_id}' is missing from explanation inputs.")
        strategy_reasons: list[str] = []
        strategy_tradeoffs: list[str] = []
        for name, metric in simulation.metrics.items():
            if metric.baseline_value is None or metric.simulated_value is None:
                continue
            delta = metric.absolute_delta
            if delta is None or delta == 0:
                continue
            direction = objective_directions.get(name)
            if direction is None:
                continue
            beneficial = (direction == "minimize" and delta < 0) or (direction == "maximize" and delta > 0)
            text = (
                f"{name}: {metric.baseline_value:g} to {metric.simulated_value:g} {metric.unit} "
                f"({delta:+g}); {metric.source_model}."
            )
            (strategy_reasons if beneficial else strategy_tradeoffs).append(text)
        strategy_explanations.append(StrategyExplanation(
            scenario_id=solution.scenario_id,
            simulation_id=solution.simulation_id,
            reasons=strategy_reasons,
            tradeoffs=strategy_tradeoffs,
        ))
        if solution is preferred:
            reasons = strategy_reasons
            tradeoffs = strategy_tradeoffs
        if not strategy_reasons and not strategy_tradeoffs:
            limitations.append(
                f"Scenario '{solution.scenario_id}' has no changed available objective values to explain."
            )
    if not preferred:
        limitations.append(
            "No explicit decision preference produced a preferred Pareto strategy; the Pareto set is reported without selecting one."
        )
    return RecommendationExplanationResult(
        optimization_id=request.optimization_result.optimization_id,
        pareto_scenario_ids=[item.scenario_id for item in pareto],
        preferred_scenario_id=preferred.scenario_id if preferred else None,
        preferred_simulation_id=preferred.simulation_id if preferred else None,
        reasons=reasons,
        tradeoffs=tradeoffs,
        strategy_explanations=strategy_explanations,
        limitations=limitations,
    )
