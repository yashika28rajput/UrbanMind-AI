from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from math import isfinite
from time import perf_counter
from pathlib import Path
from typing import Any

from app.phase10.schemas import Scenario
from app.phase9.graph.state import UrbanState
from app.phase11.adapter import adapt_simulation_request
from app.phase11.schemas import (
    MetricDelta,
    ScenarioMetricEstimate,
    SimulationInput,
    SimulationMetadata,
    SimulationRequest,
    SimulationResult,
    SimulationUncertainty,
    SimulatedUrbanState,
)
from app.services import prediction_service
from app.services.prediction_service import CARBON_REDUCTION_UNAVAILABLE_REASON

HEALTH_RISK_UNIT = "composite score (0–1)"
HEALTH_RISK_MODEL_SCALE = 100.0

METRIC_SPECS = {
    "aqi": ("AQI", "unavailable: no validated impact or scenario features"),
    "temperature": ("°C", "unavailable: no validated impact or scenario features"),
    "green_cover": ("%", "unavailable: no validated impact or scenario features"),
    "carbon_impact": ("tCO2e/year", "unavailable: no validated impact or scenario features"),
    "carbon_emissions": ("tCO2e/year", "unavailable: no provenance-backed emission estimate"),
    "health_risk": (HEALTH_RISK_UNIT, "unavailable: no validated impact or scenario features"),
    "health_benefit": (f"inverse {HEALTH_RISK_UNIT}", "derived from health-risk score"),
    "cost": ("INR", "scenario cost estimate"),
    "population_exposure": ("people", "unavailable: no validated exposure estimate"),
    "execution_time": ("years", "scenario implementation parameters"),
    "sustainability": ("score", "unavailable: no validated sustainability estimate"),
}

MODEL_INPUTS = {
    "aqi": ("aqi", prediction_service.AQI_MODEL_PATH, prediction_service.predict_aqi),
    "temperature": ("urban_heat", prediction_service.URBAN_HEAT_MODEL_PATH, prediction_service.predict_urban_heat),
    "green_cover": ("green_cover", prediction_service.GREEN_COVER_MODEL_PATH, prediction_service.predict_green_cover),
    "carbon_impact": ("carbon", prediction_service.CARBON_REDUCTION_MODEL_PATH, prediction_service.estimate_carbon_reduction),
    "health_risk": ("health_risk", prediction_service.HEALTH_RISK_MODEL_PATH, prediction_service.predict_health_risk),
}
MODEL_INFO_PATHS = {
    "aqi": prediction_service.AQI_MODEL_INFO_PATH,
    "temperature": prediction_service.URBAN_HEAT_MODEL_INFO_PATH,
    "green_cover": prediction_service.GREEN_COVER_MODEL_INFO_PATH,
    "carbon_impact": prediction_service.CARBON_REDUCTION_MODEL_INFO_PATH,
    "health_risk": prediction_service.HEALTH_RISK_MODEL_INFO_PATH,
}
IMPACT_UNIT_FIELDS = {
    "aqi": "expected_aqi_change",
    "temperature": "expected_uhi_change",
    "green_cover": "expected_green_cover_change",
    "carbon_impact": "expected_carbon_reduction",
    "carbon_emissions": "expected_carbon_reduction",
    "health_risk": "expected_health_risk_change",
}
@lru_cache(maxsize=16)
def _cached_model_digest(path_text: str, modified_ns: int, size: int) -> str:
    digest = hashlib.sha256()
    with Path(path_text).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _model_digest(path: Path) -> str:
    stat = path.stat()
    return _cached_model_digest(str(path), stat.st_mtime_ns, stat.st_size)


def _input_baseline(state: UrbanState, inputs: SimulationInput) -> dict[str, float]:
    baseline = dict(inputs.baseline_metrics)
    if state.forecasts:
        if state.forecasts.aqi_prediction is not None:
            baseline.setdefault("aqi", state.forecasts.aqi_prediction)
        if state.forecasts.uhi_prediction is not None:
            baseline.setdefault("temperature", state.forecasts.uhi_prediction)
    if state.health_analysis and state.health_analysis.affected_population:
        baseline.setdefault("population_exposure", float(state.health_analysis.affected_population))
    return baseline


def _scenario_parameters(scenario: Scenario) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for intervention in scenario.interventions:
        params.update(intervention.parameters)
    params.update(scenario.implementation_parameters if not scenario.interventions else {})
    return params


def _feature_map(
    scenario: Scenario,
    inputs: SimulationInput,
) -> dict[str, dict[str, float]]:
    result = {
        name: {**inputs.model_features.get(name, {}), **features}
        for name, features in inputs.scenario_model_features.items()
    }
    scenario_overrides = inputs.scenario_features_by_id.get(scenario.scenario_id)
    if scenario_overrides is not None:
        for model_name, features in scenario_overrides.items():
            result.setdefault(model_name, dict(inputs.model_features.get(model_name, {}))).update(features)
    else:
        for intervention in scenario.interventions:
            overrides = inputs.scenario_features_by_intervention.get(intervention.intervention_id)
            if overrides:
                for model_name, features in overrides.items():
                    result.setdefault(model_name, dict(inputs.model_features.get(model_name, {}))).update(features)
    updates = _scenario_parameters(scenario).get("model_feature_updates", {})
    if isinstance(updates, dict):
        for model_name, values in updates.items():
            if isinstance(values, dict):
                result[model_name] = {**inputs.model_features.get(model_name, {}), **values}
    return result


def _read_model_prediction(
    metric: str,
    features: dict[str, float],
) -> tuple[float, str, float | None] | None:
    model_name, model_path, predictor = MODEL_INPUTS[metric]
    info_path = MODEL_INFO_PATHS[metric]
    if not model_path.exists() or not info_path.exists():
        return None
    with info_path.open("r", encoding="utf-8") as handle:
        metadata = json.load(handle)
    required_features = metadata.get("features")
    if not isinstance(required_features, list) or not required_features:
        raise ValueError(f"{model_name} model metadata does not include a feature list.")
    if set(required_features) - features.keys():
        return None
    try:
        result = predictor(features)
    except ValueError as exc:
        if metric == "carbon_impact" and str(exc) == CARBON_REDUCTION_UNAVAILABLE_REASON:
            return None
        if "Missing required features" in str(exc) or "No valid features" in str(exc):
            return None
        raise
    model_value = float(result["predicted_value"])
    uncertainty = None
    if metric in {"aqi", "temperature"}:
        metrics = metadata.get("test_metrics", metadata.get("validation_metrics", {}))
        uncertainty = metrics.get("mae", metrics.get("MAE"))
    return model_value, str(result.get("model_name") or model_name), uncertainty


def _apply_provenance_backed_impact(baseline: float | None, delta: float) -> float | None:
    if baseline is None:
        return None
    return baseline + delta


def _estimate_pair(
    metric: str,
    baseline: float | None,
    baseline_features: dict[str, float],
    scenario_features: dict[str, float],
    scenario_delta: float | None,
) -> tuple[float | None, str, float | None, float | None]:
    before = _read_model_prediction(metric, baseline_features) if baseline_features else None
    after = _read_model_prediction(metric, scenario_features) if scenario_features else None
    if after:
        if metric == "health_risk":
            if before is None:
                if scenario_delta is None:
                    return baseline, "unavailable: comparable baseline health-risk model features are required", None, None
            else:
                return (
                    before[0] / HEALTH_RISK_MODEL_SCALE,
                    f"{metric} model: {after[1]}",
                    after[0] / HEALTH_RISK_MODEL_SCALE,
                    after[2],
                )
        else:
            return before[0] if before else baseline, f"{metric} model: {after[1]}", after[0], after[2]
    if baseline is None:
        if before:
            baseline = before[0]
        else:
            if scenario_delta is not None:
                if metric == "carbon_impact":
                    return None, "Phase 10 provenance-backed impact estimate", scenario_delta, None
                return None, "Phase 10 provenance-backed impact estimate", None, None
        return None, "unavailable: provide a numeric baseline or complete model features", None, None
    if scenario_delta is None:
        return baseline, "unavailable: no validated impact estimate or changed model features", None, None
    # Scenario impact estimates are admitted by Phase 10 only when provenance is present.
    simulated = _apply_provenance_backed_impact(baseline, scenario_delta)
    return baseline, "Phase 10 provenance-backed impact estimate", simulated, None


def _unavailable_reason(
    metric: str,
    *,
    scenario: Scenario,
    baseline_available: bool,
    baseline_features: dict[str, float],
    scenario_features: dict[str, float],
) -> str:
    if metric == "carbon_impact":
        return CARBON_REDUCTION_UNAVAILABLE_REASON
    if metric in MODEL_INPUTS:
        if scenario.interventions and not scenario_features:
            return (
                "No validated intervention-to-model-feature mapping or provenance-backed "
                "impact estimate is available; the Digital Twin baseline is not treated as "
                "an intervention effect."
            )
        if scenario.interventions and not baseline_features:
            return "The model requires a complete baseline feature vector, which is unavailable."
        if not baseline_available and not baseline_features:
            return "No Digital Twin baseline or complete model feature vector is available."
        return "The required model features are incomplete and no validated estimate is available."
    if metric == "carbon_emissions":
        return (
            "Carbon emissions are unavailable: no scenario-specific absolute baseline emissions "
            "inventory or activity data and applicable source-specific emission factors were supplied."
        )
    if metric == "cost":
        return "No provenance-backed scenario cost estimate is available."
    if metric == "population_exposure":
        return (
            "The Digital Twin supplies ward population, not exposed population; no validated "
            "scenario exposure estimate is available."
        )
    if metric == "health_benefit":
        return "Health benefit cannot be derived without a simulated health-risk value."
    if metric == "execution_time":
        return "No implementation or deployment duration was supplied."
    if metric == "sustainability":
        return "No validated sustainability scoring method or estimate is available."
    return f"No validated simulated value is available for {metric}."


def _apply_planner_schedule_estimate(request: SimulationRequest) -> SimulationRequest:
    schedule = request.scenario.provenance.get("implementation_schedule")
    if not isinstance(schedule, dict) or "execution_time" in request.simulation_input.scenario_estimates:
        return request
    estimate = ScenarioMetricEstimate.model_validate({
        "value": schedule.get("duration_years"),
        "unit": "years",
        "source_type": "user_input",
        "source": schedule.get("source") or "Planner-supplied implementation schedule",
    })
    inputs = request.simulation_input.model_dump(mode="python")
    inputs["scenario_estimates"] = {
        **inputs["scenario_estimates"],
        "execution_time": estimate,
    }
    return request.model_copy(update={
        "simulation_input": SimulationInput.model_validate(inputs),
    })


def run_simulation(request: SimulationRequest) -> SimulationResult:
    started = perf_counter()
    request = adapt_simulation_request(request)
    request = _apply_planner_schedule_estimate(request)
    state, scenario, inputs = request.urban_state, request.scenario, request.simulation_input
    baseline_values = _input_baseline(state, inputs)
    scenario_features = _feature_map(scenario, inputs)
    baseline_state = SimulatedUrbanState(
        city=scenario.city or state.request.city,
        zone=scenario.zone if scenario.zone is not None else state.request.zone or None,
        aqi=baseline_values.get("aqi"),
        temperature=baseline_values.get("temperature"),
        green_cover=baseline_values.get("green_cover"),
        carbon_impact=baseline_values.get("carbon_impact"),
        carbon_emissions=baseline_values.get("carbon_emissions"),
        health_risk=baseline_values.get("health_risk"),
        health_benefit=-baseline_values["health_risk"] if "health_risk" in baseline_values else None,
        cost=baseline_values.get("cost"),
        population_exposure=baseline_values.get("population_exposure"),
        execution_time=None,
        sustainability=baseline_values.get("sustainability"),
    )

    impacts = scenario.expected_impacts
    impact_deltas = {
        "aqi": impacts.expected_aqi_change if impacts else None,
        "temperature": impacts.expected_uhi_change if impacts else None,
        "green_cover": impacts.expected_green_cover_change if impacts else None,
        "carbon_impact": impacts.expected_carbon_reduction if impacts else None,
        "carbon_emissions": -impacts.expected_carbon_reduction if impacts and impacts.expected_carbon_reduction is not None else None,
        "health_risk": impacts.expected_health_risk_change if impacts else None,
        "health_benefit": None,
        "cost": None,
        "population_exposure": None,
        "execution_time": None,
        "sustainability": None,
    }
    params = _scenario_parameters(scenario)
    raw_duration = next(
        (params[key] for key in ("implementation_period_years", "deployment_period_years") if key in params),
        None,
    )
    try:
        duration = float(raw_duration) if raw_duration is not None and not isinstance(raw_duration, bool) else None
    except (TypeError, ValueError):
        duration = None
    if duration is not None and (not isfinite(duration) or duration <= 0):
        duration = None
    simulated_values: dict[str, float | None] = {}
    metric_results: dict[str, MetricDelta] = {}
    uncertainty: list[SimulationUncertainty] = []
    model_versions: dict[str, str] = {}

    for metric, (unit, default_source) in METRIC_SPECS.items():
        impact_unit_field = IMPACT_UNIT_FIELDS.get(metric)
        if impacts and impact_unit_field:
            unit = impacts.units.get(metric, impacts.units.get(impact_unit_field, unit))
        if metric == "health_risk":
            unit = HEALTH_RISK_UNIT
        base = getattr(baseline_state, metric)
        source = default_source
        model_error = None
        unavailable_override = None
        impact_delta = impact_deltas[metric]
        health_risk_impact_unit = (
            impacts.units.get("health_risk", impacts.units.get("expected_health_risk_change"))
            if impacts else None
        )
        if metric == "health_risk":
            if base is not None and not 0.0 <= base <= 1.0:
                base = None
                impact_delta = None
                unavailable_override = "The health-risk baseline is outside the Digital Twin composite score scale (0–1)."
            if impact_delta is not None and health_risk_impact_unit != HEALTH_RISK_UNIT:
                impact_delta = None
                unavailable_override = (
                    f"The health-risk impact estimate must declare units as {HEALTH_RISK_UNIT}."
                )
        if metric in MODEL_INPUTS:
            model_name, _, _ = MODEL_INPUTS[metric]
            baseline_features = inputs.model_features.get(model_name, {})
            candidate_features = scenario_features.get(model_name, {})
            base, source, simulated, model_error = _estimate_pair(
                metric, base, baseline_features, candidate_features, impact_delta
            )
            if (
                metric == "health_risk"
                and candidate_features
                and not baseline_features
                and simulated is None
            ):
                unavailable_override = (
                    "A comparable baseline health-risk model feature vector is required "
                    "to compare the scenario prediction on the Digital Twin composite score scale (0–1)."
                )
            if metric == "health_risk" and simulated is not None and not 0.0 <= simulated <= 1.0:
                simulated = None
                unavailable_override = "The health-risk result is outside the Digital Twin composite score scale (0–1)."
            if source.startswith(f"{metric} model:"):
                model_versions[model_name] = _model_digest(MODEL_INPUTS[metric][1])
        elif metric == "cost":
            if scenario.estimated_cost:
                unit = scenario.estimated_cost.currency
            simulated = (
                scenario.estimated_cost.total_estimated_cost
                if scenario.estimated_cost and scenario.estimated_cost.total_estimated_cost is not None
                else None
            )
            source = (
                "Phase 10 cost estimate"
                if scenario.estimated_cost and scenario.estimated_cost.total_estimated_cost is not None
                else "Business-as-usual baseline state" if not scenario.interventions and base is not None
                else "unavailable: no validated cost estimate"
            )
            if scenario.estimated_cost is None and not scenario.interventions:
                simulated = base
        elif metric == "execution_time":
            base = None
            simulated = duration
            source = "scenario implementation period" if duration is not None else "unavailable: no duration supplied"
        else:
            simulated = base + impact_deltas[metric] if base is not None and impact_deltas[metric] is not None else (
                base if metric == "execution_time" and base is not None else None
            )
            if impact_deltas[metric] is not None:
                source = "Phase 10 provenance-backed impact estimate"
            if metric == "carbon_emissions" and base is None:
                simulated = None
            if metric == "carbon_impact" and impact_deltas[metric] is not None and base is None:
                simulated = impact_deltas[metric]
            if metric == "health_benefit":
                health_metric = metric_results.get("health_risk")
                comparison_available = bool(
                    health_metric
                    and health_metric.availability == "available"
                    and health_metric.baseline_value is not None
                    and health_metric.simulated_value is not None
                    and health_metric.absolute_delta is not None
                )
                if comparison_available and health_metric is not None:
                    base = -health_metric.baseline_value
                    simulated = -health_metric.simulated_value
                else:
                    base = None
                    simulated = None
                    unavailable_override = "Health benefit requires a comparable baseline and simulated health-risk score."
        estimate = inputs.scenario_estimates.get(metric)
        if estimate is not None:
            if metric == "health_risk" and (
                estimate.unit != HEALTH_RISK_UNIT
                or not 0.0 <= estimate.value <= 1.0
                or base is None
                or not 0.0 <= base <= 1.0
            ):
                simulated = None
                unavailable_override = (
                    f"A comparable health-risk estimate must use {HEALTH_RISK_UNIT} and have a baseline on that scale."
                )
            elif metric == "health_benefit" and unavailable_override:
                simulated = None
            else:
                simulated = estimate.value
                source = (
                    f"{estimate.model_name} ({estimate.model_version})"
                    if estimate.model_name and estimate.model_version
                    else f"{estimate.source_type}: {estimate.source}"
                )
                unit = estimate.unit
                model_error = estimate.uncertainty
                if estimate.model_name and estimate.model_version:
                    model_versions[estimate.model_name] = estimate.model_version
        if not scenario.interventions and simulated is None and base is not None:
            simulated = base
            source = inputs.baseline_sources.get(metric, "Business-as-usual baseline state")
        elif simulated is None and metric in inputs.baseline_sources and source.startswith("unavailable:"):
            source = inputs.baseline_sources[metric]
        simulated_values[metric] = simulated
        if metric == "health_risk":
            delta = simulated - base if simulated is not None and base is not None else None
        else:
            delta = simulated - base if simulated is not None and base is not None else (
                impact_deltas[metric] if metric != "health_benefit" and impact_deltas[metric] is not None else None
            )
        metric_results[metric] = MetricDelta(
            baseline_value=base,
            simulated_value=simulated,
            absolute_delta=delta,
            percentage_delta=(delta / abs(base) * 100.0) if delta is not None and base not in (None, 0) else None,
            unit=unit,
            source_model=source,
            confidence=estimate.confidence if estimate is not None else None,
            uncertainty=model_error,
            availability="available" if simulated is not None else "unavailable",
            availability_reason=(
                None
                if simulated is not None
                else unavailable_override or _unavailable_reason(
                    metric,
                    scenario=scenario,
                    baseline_available=base is not None,
                    baseline_features=inputs.model_features.get(
                        MODEL_INPUTS[metric][0], {}
                    ) if metric in MODEL_INPUTS else {},
                    scenario_features=scenario_features.get(
                        MODEL_INPUTS[metric][0], {}
                    ) if metric in MODEL_INPUTS else {},
                )
            ),
        )
        if model_error is not None:
            uncertainty.append(SimulationUncertainty(
                metric=metric,
                method="reported test-set MAE",
                value=float(model_error),
                unit=unit,
                note="Model evaluation error; not a calibrated confidence interval.",
            ))

    for metric, estimate in inputs.scenario_estimates.items():
        if metric in metric_results:
            continue
        base = baseline_values.get(metric)
        delta = estimate.value - base if base is not None else None
        metric_results[metric] = MetricDelta(
            baseline_value=base,
            simulated_value=estimate.value,
            absolute_delta=delta,
            percentage_delta=(delta / abs(base) * 100.0) if delta is not None and base != 0 else None,
            unit=estimate.unit,
            source_model=(
                f"{estimate.model_name} ({estimate.model_version})"
                if estimate.model_name and estimate.model_version
                else f"{estimate.source_type}: {estimate.source}"
            ),
            confidence=estimate.confidence,
            uncertainty=estimate.uncertainty,
            availability="available",
        )
        if estimate.model_name and estimate.model_version:
            model_versions[estimate.model_name] = estimate.model_version
        simulated_values[metric] = estimate.value

    simulated_state = SimulatedUrbanState(
        city=baseline_state.city,
        zone=baseline_state.zone,
        **simulated_values,
    )
    assumptions = list(dict.fromkeys(
        (scenario.assumptions or [])
        + (impacts.assumptions if impacts else [])
        + ["No empirical impact is inferred when neither model feature changes nor a provenance-backed Phase 10 estimate is supplied."]
    ))
    if impacts:
        for estimate in impacts.provenance:
            if estimate.model_name and estimate.model_version:
                model_versions[estimate.model_name] = estimate.model_version
    canonical = json.dumps(
        {
            "engine_version": "phase11-v1",
            "request": request.model_dump(mode="json"),
            "model_versions": model_versions,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    reproducibility_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return SimulationResult(
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        workflow_id=state.workflow_id,
        status="completed" if any(item.availability == "available" for item in metric_results.values()) else "partial",
        baseline_state=baseline_state,
        simulated_state=simulated_state,
        metrics=metric_results,
        uncertainty=uncertainty,
        metadata=SimulationMetadata(
            model_versions=model_versions,
            engine_version="phase11-v1",
            reproducibility_key=reproducibility_key,
            duration_ms=(perf_counter() - started) * 1000,
            assumptions=assumptions,
        ),
    )
