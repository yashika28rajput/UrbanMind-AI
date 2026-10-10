from __future__ import annotations

import itertools
import logging
import re
from math import isfinite
from time import perf_counter
from typing import Any

from app.phase10.catalog import InterventionCatalog, intervention_catalog, normalize_intervention
from app.phase10.schemas import (
    InterventionDefinition,
    InterventionGenerationDiagnostic,
    Scenario,
    ScenarioEvidence,
    ScenarioGenerationRequest,
    ScenarioIntervention,
    ScenarioObjectives,
    ScenarioSet,
)
from app.phase9.graph.state import UrbanState
from app.services.prediction_service import CARBON_REDUCTION_UNAVAILABLE_REASON

logger = logging.getLogger(__name__)

PROBLEM_PATTERNS: dict[str, tuple[str, ...]] = {
    "high_pm25": (r"\bpm\s*2\.?5\b", r"\bhigh\s+pm", r"\bfine particulate"),
    "high_aqi": (r"\bhigh\s+aqi\b", r"\bpoor air quality\b", r"\bair pollution\b"),
    "high_uhi": (
        r"\bhigh\s+uhi\b",
        r"\burban heat island\b",
        r"\bexcessive urban heat\b",
        r"\bheat stress\b",
        r"\bhigh heat\b",
    ),
    "low_green_cover": (
        r"\blow green cover\b",
        r"\binsufficient green cover\b",
        r"\blimited green cover\b",
        r"\blimited tree cover\b",
        r"\binsufficient tree cover\b",
    ),
    "high_traffic_emissions": (r"\btraffic emissions?\b", r"\bvehicle emissions?\b", r"\btraffic pollution\b"),
    "high_carbon_emissions": (r"\bcarbon emissions?\b", r"\bhigh emissions?\b"),
    "high_population_exposure": (r"\bpopulation exposure\b", r"\bexposed population\b"),
    "health_risk_hotspot": (
        r"\bhealth risks?\b",
        r"\bhealth-risk hotspot\b",
        r"\brespiratory risks?\b",
        r"\bpublic health\b",
    ),
    "high_energy_demand": (r"\bhigh energy demand\b", r"\benergy consumption\b"),
}

OBJECTIVES_BY_PROBLEM: dict[str, list[str]] = {
    "high_pm25": ["reduce_pm25"],
    "high_aqi": ["improve_air_quality"],
    "high_uhi": ["reduce_urban_heat"],
    "low_green_cover": ["increase_green_cover"],
    "high_traffic_emissions": ["reduce_traffic_emissions"],
    "high_carbon_emissions": ["reduce_carbon_emissions"],
    "high_population_exposure": ["reduce_population_exposure"],
    "health_risk_hotspot": ["reduce_health_risk"],
    "high_energy_demand": ["reduce_energy_demand"],
}

POLLUTANTS_BY_PROBLEM = {
    "high_pm25": "PM2.5",
    "high_aqi": "PM2.5",
}


def detect_problems(
    state: UrbanState,
    request: ScenarioGenerationRequest,
) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    supplied_problems = list(request.problems)
    extra_problems = getattr(state, "identified_problems", [])
    if not supplied_problems and isinstance(extra_problems, list):
        supplied_problems = [str(problem).strip() for problem in extra_problems if str(problem).strip()]

    for value in supplied_problems:
        normalized = normalize_intervention(value)
        if normalized in PROBLEM_PATTERNS:
            problems.append(normalized)
            continue
        matches = [
            problem
            for problem, patterns in PROBLEM_PATTERNS.items()
            if any(re.search(pattern, value.lower()) for pattern in patterns)
        ]
        problems.extend(matches or [value])

    for text in (request.problem_statement or "", state.request.query or ""):
        lowered = text.lower()
        problems.extend(
            problem
            for problem, patterns in PROBLEM_PATTERNS.items()
            if any(re.search(pattern, lowered) for pattern in patterns)
        )
    if not problems:
        raise ValueError("No recognized urban problem was supplied or detected.")
    return list(dict.fromkeys(problems)), []


def identify_objectives(problems: list[str], requested: list[str]) -> ScenarioObjectives:
    primary = list(dict.fromkeys(requested or [
        objective
        for problem in problems
        for objective in OBJECTIVES_BY_PROBLEM.get(problem, [])
    ]))
    secondary = list(dict.fromkeys(
        objective
        for problem in problems
        for objective in OBJECTIVES_BY_PROBLEM.get(problem, [])
        if objective not in primary
    ))
    return ScenarioObjectives(primary=primary, secondary=secondary)


def _parameters_for(
    definition: InterventionDefinition,
    request: ScenarioGenerationRequest,
    variant: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requested_values: dict[str, Any] = {}
    for key, values in request.intervention_parameters.items():
        if normalize_intervention(key) in {
            normalize_intervention(definition.intervention_id),
            normalize_intervention(definition.name),
            *(normalize_intervention(alias) for alias in definition.aliases),
        }:
            requested_values.update(values)
    if variant:
        requested_values.update(variant)
    return requested_values


def _candidate_definitions(
    problems: list[str],
    request: ScenarioGenerationRequest,
    catalog: InterventionCatalog,
) -> tuple[list[InterventionDefinition], list[str], list[InterventionGenerationDiagnostic]]:
    definitions: list[InterventionDefinition] = []
    warnings: list[str] = []
    diagnostics: list[InterventionGenerationDiagnostic] = []
    requested_ids = {normalize_intervention(value) for value in request.requested_interventions}
    for name in request.requested_interventions:
        definition = catalog.get(name)
        if definition is None:
            reason = "No canonical intervention or alias matched the configured catalog."
            warnings.append(f"Intervention '{name}' is not present in the configured catalog and was omitted.")
            diagnostics.append(InterventionGenerationDiagnostic(
                requested_name=name,
                matched=False,
                rejected=True,
                reason=reason,
            ))
        elif set(problems).intersection(definition.target_problems):
            definitions.append(definition)
            diagnostics.append(InterventionGenerationDiagnostic(
                requested_name=name,
                canonical_intervention_id=definition.intervention_id,
                matched=True,
                rejected=False,
                reason="Matched the catalog and the identified problems; candidate queued for validation.",
            ))
        else:
            reason = (
                f"Catalog entry '{definition.name}' does not target any identified problem: "
                f"{', '.join(problems)}."
            )
            warnings.append(f"Intervention '{name}' does not address the identified problems and was omitted.")
            diagnostics.append(InterventionGenerationDiagnostic(
                requested_name=name,
                canonical_intervention_id=definition.intervention_id,
                matched=True,
                rejected=True,
                reason=reason,
            ))

    for definition in catalog.relevant_to(problems):
        normalized_ids = {
            normalize_intervention(definition.intervention_id),
            normalize_intervention(definition.name),
            *(normalize_intervention(alias) for alias in definition.aliases),
        }
        if normalized_ids.intersection(requested_ids):
            continue
        definitions.append(definition)
    unique: dict[str, InterventionDefinition] = {}
    for definition in definitions:
        unique.setdefault(definition.intervention_id, definition)
    return list(unique.values()), warnings, diagnostics


def _validate_parameters(
    definition: InterventionDefinition,
    parameters: dict[str, Any],
    request: ScenarioGenerationRequest,
    state: UrbanState,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    review: list[str] = []
    allowed = set(definition.required_parameters + definition.optional_parameters)
    unknown = sorted(set(parameters) - allowed)
    if unknown:
        failures.append(f"Unsupported parameters for {definition.name}: {', '.join(unknown)}.")
    missing = [name for name in definition.required_parameters if name not in parameters]
    if missing:
        review.append(f"Required implementation parameters are missing: {', '.join(missing)}.")
    for key, value in parameters.items():
        if key in {"implementation_period_years", "deployment_period_years"}:
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(float(value))
                or value <= 0
            ):
                failures.append(f"Parameter '{key}' must be a positive finite number of years.")
            continue
        if isinstance(value, bool) or value is None:
            failures.append(f"Parameter '{key}' must have a value.")
        elif isinstance(value, (int, float)) and value <= 0:
            failures.append(f"Parameter '{key}' must be greater than zero.")
        elif key in {"number_of_buses", "building_count", "tree_density"} and (
            not isinstance(value, int) or isinstance(value, bool)
        ):
            failures.append(f"Parameter '{key}' must be an integer.")
        elif isinstance(value, str) and not value.strip():
            failures.append(f"Parameter '{key}' must not be empty.")
        elif isinstance(value, list) and not value:
            failures.append(f"Parameter '{key}' must not be an empty list.")

    constraints = request.constraints
    available_land = constraints.available_land_hectares
    if available_land is not None:
        area = parameters.get("area_hectares", parameters.get("land_required_hectares"))
        if isinstance(area, (int, float)) and not isinstance(area, bool) and area > available_land:
            failures.append(f"Required land ({area} ha) exceeds available land ({available_land} ha).")
        elif area is None and "area_hectares" in definition.required_parameters:
            review.append("Land feasibility cannot be checked until area_hectares is provided.")
    horizon = constraints.time_horizon_years
    if horizon is not None:
        duration = request.implementation_period_years
        if duration is None:
            duration = next(
                (parameters[key] for key in ("implementation_period_years", "deployment_period_years") if key in parameters),
                None,
            )
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not isfinite(float(duration)):
            duration = None
        if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration > horizon:
            failures.append(f"Implementation duration ({duration} years) exceeds the planning horizon ({horizon} years).")
        elif duration is None and any(
            key in definition.required_parameters
            for key in ("implementation_period_years", "deployment_period_years")
        ):
            review.append("Time feasibility cannot be checked until implementation duration is provided.")

    urban_policy = state.policy_analysis
    conflicts = urban_policy.policy_conflicts if urban_policy else []
    constraints_from_state = request.constraints.policy_constraints
    if conflicts:
        failures.extend(f"Policy conflict: {conflict}" for conflict in conflicts)
    if constraints_from_state:
        review.append("Policy constraints require confirmation by the policy service: " + "; ".join(constraints_from_state))
    if constraints.budget_limit is not None:
        review.append("Budget feasibility cannot be verified because no validated cost estimate is available.")
    return failures, review


def _status(failures: list[str], review: list[str]) -> str:
    if failures:
        return "INVALID"
    if review:
        return "REQUIRES_REVIEW"
    return "SIMULATION_READY"


def _make_scenario(
    *,
    definitions: list[InterventionDefinition],
    parameter_sets: list[dict[str, Any]],
    state: UrbanState,
    request: ScenarioGenerationRequest,
    problems: list[str],
    evidence_ids: list[str],
    workflow_id: str,
    scenario_name: str | None = None,
) -> Scenario:
    failures: list[str] = []
    review: list[str] = []
    constraints = [
        f"Budget limit: {request.constraints.budget_limit} {request.constraints.currency}"
        for _ in [0]
        if request.constraints.budget_limit is not None
    ]
    if request.constraints.available_land_hectares is not None:
        constraints.append(f"Available land: {request.constraints.available_land_hectares} hectares")
    if request.constraints.time_horizon_years is not None:
        constraints.append(f"Planning horizon: {request.constraints.time_horizon_years} years")
    constraints.extend(request.constraints.policy_constraints)

    interventions: list[ScenarioIntervention] = []
    target_problems: list[str] = []
    for definition, parameters in zip(definitions, parameter_sets):
        item_failures, item_review = _validate_parameters(definition, parameters, request, state)
        failures.extend(item_failures)
        review.extend(item_review)
        target_problems.extend(problem for problem in definition.target_problems if problem in problems)
        interventions.append(ScenarioIntervention(
            intervention_id=definition.intervention_id,
            name=definition.name,
            parameters=parameters,
            parameter_sources={key: "user_input" for key in parameters},
            definition_version=definition.version,
        ))

    if not evidence_ids:
        review.append("No indexed evidence was retrieved for this request.")
    if definitions and request.implementation_period_years is None and not any(
        key in parameters
        for parameters in parameter_sets
        for key in ("implementation_period_years", "deployment_period_years")
    ):
        review.append("Implementation duration is unavailable; execution time cannot be optimized.")
    if not state.policy_analysis:
        review.append("Policy conflicts have not been evaluated for this scenario.")
    else:
        conflicts = state.policy_analysis.policy_conflicts
        failures.extend(f"Policy conflict: {conflict}" for conflict in conflicts)

    kind = "baseline" if not definitions else (
        "combined_strategy" if len(definitions) > 1 else definitions[0].category
    )
    scenario_name = scenario_name or (
        "Business as Usual" if not definitions else " + ".join(item.name for item in definitions)
    )
    component_ids = [item.intervention_id for item in interventions]
    status = "SIMULATION_READY" if not definitions else _status(failures, review)
    return Scenario(
        name=scenario_name,
        description=(
            "No new intervention is introduced; use the existing urban state as a reference baseline."
            if not definitions
            else "Candidate intervention configuration for downstream policy review and scenario simulation."
        ),
        city=request.city or state.request.city,
        zone=request.zone if request.zone is not None else state.request.zone or None,
        intervention_type=kind,
        interventions=interventions,
        components=component_ids,
        target_problems=list(dict.fromkeys(target_problems or problems)),
        scale={
            item.intervention_id: item.parameters
            for item in interventions
        },
        implementation_parameters={
            item.intervention_id: item.parameters for item in interventions
        },
        constraint_values=request.constraints,
        required_resources=[],
        assumptions=[
            "No cost or impact estimates are generated in Phase 10.",
            *(
                ["Implementation duration is planner-supplied and represents the planned schedule, not measured elapsed time."]
                if definitions and request.implementation_period_years is not None
                else []
            ),
            *([f"Implementation parameters for {item.name} remain unspecified." for item in interventions
               if any(param not in item.parameters for param in next(
                   definition.required_parameters for definition in definitions
                   if definition.intervention_id == item.intervention_id
               ))]),
        ],
        carbon_reduction_availability_reason=CARBON_REDUCTION_UNAVAILABLE_REASON,
        constraints=list(dict.fromkeys(constraints + failures + review)),
        evidence_ids=evidence_ids,
        source_ids=evidence_ids,
        status=status,
        provenance={
            "workflow_id": workflow_id,
            "urban_state_version": request.urban_state_version,
            "intervention_catalog_version": "1.0",
            "generation_method": "deterministic_catalog",
            **({
                "implementation_schedule": {
                    "duration_years": request.implementation_period_years,
                    "source_type": "user_input",
                    "source": "Planner-supplied implementation schedule",
                }
            } if definitions and request.implementation_period_years is not None else {}),
        },
    )


def generate_scenario_set(
    urban_state: UrbanState,
    request: ScenarioGenerationRequest,
    *,
    evidence: list[ScenarioEvidence] | None = None,
    knowledge_graph_interventions: list[str] | None = None,
    warnings: list[str] | None = None,
    catalog: InterventionCatalog = intervention_catalog,
) -> ScenarioSet:
    started_at = perf_counter()
    problems, detected_warnings = detect_problems(urban_state, request)
    objectives = identify_objectives(problems, request.objectives)
    definitions, candidate_warnings, intervention_diagnostics = _candidate_definitions(
        problems,
        request,
        catalog,
    )
    graph_interventions = {
        normalize_intervention(value) for value in (knowledge_graph_interventions or [])
    }
    if graph_interventions:
        requested_order = {
            normalized: index
            for index, value in enumerate(request.requested_interventions)
            for normalized in [normalize_intervention(value)]
        }

        def candidate_order(item: InterventionDefinition) -> tuple[int, int, str]:
            aliases = {
                normalize_intervention(item.intervention_id),
                normalize_intervention(item.name),
                *(normalize_intervention(alias) for alias in item.aliases),
            }
            requested_rank = min(
                (requested_order[alias] for alias in aliases if alias in requested_order),
                default=len(requested_order),
            )
            graph_rank = 0 if aliases.intersection(graph_interventions) else 1
            return requested_rank, graph_rank, item.intervention_id

        definitions.sort(key=lambda item: (
            *candidate_order(item),
        ))

    result_warnings = list(dict.fromkeys((warnings or []) + detected_warnings + candidate_warnings))
    evidence = evidence or []
    evidence_ids = [item.evidence_id for item in evidence]
    workflow_id = request.workflow_id or urban_state.workflow_id
    scenario_items: list[Scenario] = []
    seen: set[tuple[Any, ...]] = set()

    def append_unique(scenario: Scenario, key: tuple[Any, ...]) -> None:
        if key not in seen and len(scenario_items) < request.max_scenarios:
            seen.add(key)
            scenario_items.append(scenario)

    if request.include_baseline:
        append_unique(
            _make_scenario(
                definitions=[],
                parameter_sets=[],
                state=urban_state,
                request=request,
                problems=problems,
                evidence_ids=evidence_ids,
                workflow_id=workflow_id,
            ),
            ("baseline",),
        )

    selected_definitions = definitions[:request.max_scenarios]
    singles: list[tuple[InterventionDefinition, dict[str, Any]]] = []
    for definition in selected_definitions:
        variant_values = next(
            (
                values
                for key, values in request.parameter_variants.items()
                if normalize_intervention(key) in {
                    normalize_intervention(definition.intervention_id),
                    normalize_intervention(definition.name),
                    *(normalize_intervention(alias) for alias in definition.aliases),
                }
            ),
            [],
        )
        variants = variant_values or [_parameters_for(definition, request)]
        for variant_index, variant in enumerate(variants):
            parameters = _parameters_for(definition, request, variant)
            label = definition.name if len(variants) == 1 else f"{definition.name} — option {variant_index + 1}"
            scenario = _make_scenario(
                definitions=[definition],
                parameter_sets=[parameters],
                state=urban_state,
                request=request,
                problems=problems,
                evidence_ids=evidence_ids,
                workflow_id=workflow_id,
                scenario_name=label,
            )
            parameter_key = tuple(sorted((key, repr(value)) for key, value in parameters.items()))
            append_unique(scenario, ("single", definition.intervention_id, parameter_key))
            singles.append((definition, parameters))

    if request.include_combinations and request.max_combination_size > 1:
        combination_count = 0
        for size in range(2, min(request.max_combination_size, len(singles)) + 1):
            for combination in itertools.combinations(singles, size):
                component_ids = tuple(sorted(item[0].intervention_id for item in combination))
                if len(set(component_ids)) != size:
                    continue
                definitions_in_combo = [item[0] for item in combination]
                parameters_in_combo = [item[1] for item in combination]
                scenario = _make_scenario(
                    definitions=definitions_in_combo,
                    parameter_sets=parameters_in_combo,
                    state=urban_state,
                    request=request,
                    problems=problems,
                    evidence_ids=evidence_ids,
                    workflow_id=workflow_id,
                )
                parameter_signature = tuple(
                    (
                        item[0].intervention_id,
                        tuple(sorted((key, repr(value)) for key, value in item[1].items())),
                    )
                    for item in combination
                )
                append_unique(scenario, ("combined", component_ids, parameter_signature))
                combination_count += 1
                if combination_count >= 2 or len(scenario_items) >= request.max_scenarios:
                    break
            if combination_count >= 2 or len(scenario_items) >= request.max_scenarios:
                break

    if not scenario_items:
        result_warnings.append("No applicable interventions were available; no scenarios were generated.")
    scenarios_by_intervention = {
        intervention.intervention_id: scenario
        for scenario in scenario_items
        for intervention in scenario.interventions
        if len(scenario.interventions) == 1
    }
    for diagnostic in intervention_diagnostics:
        if diagnostic.rejected or diagnostic.canonical_intervention_id is None:
            continue
        scenario = scenarios_by_intervention.get(diagnostic.canonical_intervention_id)
        if scenario is None:
            diagnostic.rejected = True
            diagnostic.reason = "Matched catalog entry but was not generated within the max_scenarios limit."
        elif scenario.status == "INVALID":
            diagnostic.rejected = True
            diagnostic.reason = "Catalog match failed validation: " + "; ".join(scenario.constraints)
        elif scenario.status == "REQUIRES_REVIEW":
            diagnostic.reason = (
                "Candidate generated but requires review: "
                + "; ".join(scenario.constraints)
            )
    invalid_count = sum(item.status == "INVALID" for item in scenario_items)
    if invalid_count:
        result_warnings.append(f"{invalid_count} scenario(s) failed validation and are not simulation-ready.")
    scenario_set = ScenarioSet(
        workflow_id=workflow_id,
        city=request.city or urban_state.request.city,
        zone=request.zone if request.zone is not None else urban_state.request.zone or None,
        problem_statement=request.problem_statement or urban_state.request.query,
        identified_problems=problems,
        objectives=objectives,
        constraints=request.constraints,
        scenarios=scenario_items,
        urban_state_version=request.urban_state_version,
        generation_duration_ms=(perf_counter() - started_at) * 1000,
        evidence=evidence,
        intervention_diagnostics=intervention_diagnostics,
        warnings=list(dict.fromkeys(result_warnings)),
        status="completed" if scenario_items else "partial",
        assumptions=[
            "Scenario generation identifies options; it does not simulate, score, rank, or optimize them.",
            "Costs and impacts remain unset unless supplied by validated downstream models.",
        ],
    )
    logger.info(
        "Scenario generation completed",
        extra={
            "request_id": scenario_set.request_id,
            "workflow_id": workflow_id,
            "city": scenario_set.city,
            "zone": scenario_set.zone,
            "identified_problems": problems,
            "candidate_count": len(definitions),
            "scenario_count": len(scenario_items),
            "invalid_count": invalid_count,
            "rejected_count": invalid_count + len(candidate_warnings),
            "execution_time_ms": scenario_set.generation_duration_ms,
        },
    )
    return scenario_set
