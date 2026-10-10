from __future__ import annotations

from math import isfinite

from app.phase11.schemas import SimulationResult
from app.phase12.schemas import (
    OptimizationRequest,
    OptimizationResult,
    ParetoSolution,
    ScenarioScore,
)


def _metric_value(simulation: SimulationResult, name: str) -> float | None:
    metric = simulation.metrics.get(name)
    value = metric.simulated_value if metric else None
    return value if value is not None and isfinite(value) else None


def _score_candidate(simulation: SimulationResult, request: OptimizationRequest) -> ScenarioScore:
    values = {objective.name: _metric_value(simulation, objective.name) for objective in request.objectives}
    sources = {
        objective.name: simulation.metrics[objective.name].source_model
        for objective in request.objectives
        if objective.name in simulation.metrics
    }
    missing_objectives = [name for name, value in values.items() if value is None]
    violations = []
    for constraint in request.constraints:
        observed = _metric_value(simulation, constraint.metric)
        if observed is None:
            violations.append(f"{constraint.name}: metric '{constraint.metric}' is unavailable.")
        elif constraint.operator == "<=" and observed > constraint.value:
            violations.append(f"{constraint.name}: {observed} exceeds {constraint.value}.")
        elif constraint.operator == ">=" and observed < constraint.value:
            violations.append(f"{constraint.name}: {observed} is below {constraint.value}.")
    return ScenarioScore(
        scenario_id=simulation.scenario_id,
        simulation_id=simulation.simulation_id,
        objective_values=values,
        objective_sources=sources,
        feasible=not violations and not missing_objectives,
        constraint_violations=violations,
        missing_objectives=missing_objectives,
    )


def _dominates(first: ScenarioScore, second: ScenarioScore, directions: dict[str, str]) -> bool:
    if not first.feasible or not second.feasible:
        return False
    no_worse = True
    strictly_better = False
    for name, direction in directions.items():
        left, right = first.objective_values[name], second.objective_values[name]
        if left is None or right is None:
            return False
        if direction == "minimize":
            no_worse &= left <= right
            strictly_better |= left < right
        else:
            no_worse &= left >= right
            strictly_better |= left > right
    return no_worse and strictly_better


def _pareto_front(scores: list[ScenarioScore], directions: dict[str, str]) -> list[list[ScenarioScore]]:
    remaining = [score for score in scores if score.feasible]
    fronts: list[list[ScenarioScore]] = []
    while remaining:
        front = [
            candidate for candidate in remaining
            if not any(_dominates(other, candidate, directions) for other in remaining if other is not candidate)
        ]
        fronts.append(front)
        front_ids = {item.simulation_id for item in front}
        remaining = [item for item in remaining if item.simulation_id not in front_ids]
    return fronts


def _crowding(front: list[ScenarioScore], objectives: list[str]) -> dict[str, float | None]:
    distances = {score.simulation_id: 0.0 for score in front}
    if len(front) <= 2:
        return {score.simulation_id: None for score in front}
    for objective in objectives:
        ordered = sorted(front, key=lambda item: item.objective_values[objective] or 0.0)
        distances[ordered[0].simulation_id] = None
        distances[ordered[-1].simulation_id] = None
        low = ordered[0].objective_values[objective]
        high = ordered[-1].objective_values[objective]
        if low is None or high is None or high == low:
            continue
        for index in range(1, len(ordered) - 1):
            if distances[ordered[index].simulation_id] is not None:
                previous_value = ordered[index - 1].objective_values[objective]
                next_value = ordered[index + 1].objective_values[objective]
                if previous_value is not None and next_value is not None:
                    distances[ordered[index].simulation_id] += (next_value - previous_value) / (high - low)
    return distances


def _decision_scores(
    front: list[ScenarioScore],
    weights: dict[str, float],
    directions: dict[str, str],
) -> dict[str, float]:
    if not weights:
        return {}
    ranges: dict[str, tuple[float, float]] = {}
    for name in weights:
        values = [item.objective_values[name] for item in front if item.objective_values.get(name) is not None]
        if values:
            ranges[name] = (min(values), max(values))
    result = {}
    for item in front:
        total = 0.0
        total_weight = 0.0
        for name, weight in weights.items():
            value = item.objective_values.get(name)
            bounds = ranges.get(name)
            if value is None or bounds is None:
                continue
            low, high = bounds
            utility = 1.0 if high == low else ((value - low) / (high - low))
            if directions.get(name) == "minimize":
                utility = 1.0 - utility
            total += utility * weight
            total_weight += weight
        if total_weight:
            result[item.simulation_id] = total / total_weight
    return result


def run_optimization(request: OptimizationRequest) -> OptimizationResult:
    names = [item.name for item in request.objectives]
    if len(names) != len(set(names)):
        raise ValueError("Objective names must be unique.")
    unknown_weights = set(request.decision_preferences) - set(names)
    if unknown_weights:
        raise ValueError(f"Decision preferences reference undefined objectives: {sorted(unknown_weights)}")
    if any(weight <= 0 for weight in request.decision_preferences.values()):
        raise ValueError("Decision preference weights must be greater than zero.")
    if any(not constraint.name.strip() for constraint in request.constraints):
        raise ValueError("Constraint names must not be empty.")
    directions = {item.name: item.direction for item in request.objectives}
    scores = [_score_candidate(item, request) for item in request.simulations]
    fronts = _pareto_front(scores, directions)
    for rank, front in enumerate(fronts, start=1):
        distances = _crowding(front, names)
        for score in front:
            score.pareto_rank = rank
            score.crowding_distance = distances[score.simulation_id]
            score.crowding_boundary = distances[score.simulation_id] is None
    pareto = fronts[0] if fronts else []
    if pareto:
        status = "completed"
    elif not scores:
        status = "no_candidates"
    elif any(score.missing_objectives and not score.constraint_violations for score in scores):
        status = "no_rankable_solutions"
    else:
        status = "no_feasible_solutions"
    decision_preferences = request.decision_preferences or {
        item.name: item.weight for item in request.objectives if item.weight is not None
    }
    decision_scores = _decision_scores(pareto, decision_preferences, directions)
    for score in pareto:
        score.decision_score = decision_scores.get(score.simulation_id)
    solutions = [
        ParetoSolution(
            scenario_id=score.scenario_id,
            simulation_id=score.simulation_id,
            objective_values={name: value for name, value in score.objective_values.items() if value is not None},
            objective_sources=score.objective_sources,
            constraint_violations=score.constraint_violations,
            pareto_rank=score.pareto_rank or 1,
            crowding_distance=score.crowding_distance,
            crowding_boundary=score.crowding_boundary,
            decision_score=score.decision_score,
        )
        for score in pareto
    ]
    return OptimizationResult(
        status=status,
        objectives=request.objectives,
        constraints=request.constraints,
        pareto_solutions=solutions,
        dominated_strategies=[score for front in fronts[1:] for score in front],
        infeasible_strategies=[score for score in scores if score.constraint_violations],
        unevaluable_strategies=[
            score for score in scores
            if score.missing_objectives and not score.constraint_violations
        ],
        scores=scores,
        decision_preferences=decision_preferences,
    )
