from __future__ import annotations

import json

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.phase10.schemas import (
    CostEstimate,
    EstimateProvenance,
    ImpactEstimate,
    Scenario,
    ScenarioGenerationRequest,
    ScenarioIntervention,
)
from app.phase11.engine import run_simulation
from app.phase11.schemas import (
    MetricDelta,
    SimulationInput,
    ScenarioMetricEstimate,
    SimulationRequest,
    SimulationResult,
    SimulationMetadata,
    SimulatedUrbanState,
)
from app.phase12.engine import run_optimization
from app.phase12.schemas import (
    ConstraintDefinition,
    ObjectiveDefinition,
    OptimizationRequest,
)
from app.phase13.engine import explain_prediction, run_counterfactual
from app.phase13 import pipeline as pipeline_module
from app.phase13.pipeline import PipelineRequest, PipelineResult
from app.phase13.schemas import CounterfactualRequest, ExplanationRequest
from app.database.urban_memory_store import Base
from app.services.prediction_service import GREEN_COVER_MODEL_INFO_PATH
from app.phase9.graph.state import UrbanState
from app.services.prediction_service import AQI_MODEL_INFO_PATH


client = TestClient(app)


def _state() -> UrbanState:
    return UrbanState(
        workflow_id="phase11-test",
        request={"query": "High AQI in TestCity", "city": "TestCity", "zone": "Ward 1"},
    )


def _scenario() -> Scenario:
    provenance = [EstimateProvenance(source_type="validated_model", source_id="test-model")]
    return Scenario(
        scenario_id="scenario-test",
        name="Test intervention",
        description="Test",
        city="TestCity",
        zone="Ward 1",
        intervention_type="green_infrastructure",
        interventions=[
            ScenarioIntervention(
                intervention_id="urban_forest_expansion",
                name="Urban Forest Expansion",
                parameters={"area_hectares": 2, "tree_density": 100},
            )
        ],
        implementation_parameters={"urban_forest_expansion": {"area_hectares": 2, "tree_density": 100}},
        estimated_cost=CostEstimate(total_estimated_cost=5000, provenance=provenance),
        expected_impacts=ImpactEstimate(
            expected_aqi_change=-10,
            expected_uhi_change=-1.5,
            expected_green_cover_change=2,
            expected_carbon_reduction=3,
            expected_health_risk_change=-2,
            provenance=provenance,
        ),
    )


def _simulation(
    scenario_id: str,
    *,
    cost: float,
    green: float,
    aqi: float = 100,
) -> SimulationResult:
    metrics = {
        "cost": MetricDelta(
            baseline_value=0, simulated_value=cost, absolute_delta=cost,
            percentage_delta=None, unit="INR", source_model="test",
        ),
        "green_cover": MetricDelta(
            baseline_value=10, simulated_value=green, absolute_delta=green - 10,
            percentage_delta=None, unit="%", source_model="test",
        ),
        "aqi": MetricDelta(
            baseline_value=120, simulated_value=aqi, absolute_delta=aqi - 120,
            percentage_delta=None, unit="AQI", source_model="test",
        ),
    }
    return SimulationResult(
        simulation_id=f"sim-{scenario_id}",
        scenario_id=scenario_id,
        scenario_version=1,
        workflow_id="test",
        status="completed",
        baseline_state=SimulatedUrbanState(city="TestCity"),
        simulated_state=SimulatedUrbanState(city="TestCity", cost=cost, green_cover=green, aqi=aqi),
        metrics=metrics,
        metadata=SimulationMetadata(reproducibility_key=scenario_id),
    )


def test_scenario_to_simulation_calculates_baseline_deltas_and_is_reproducible() -> None:
    request = SimulationRequest(
        urban_state=_state(),
        scenario=_scenario(),
        simulation_input=SimulationInput(
            baseline_metrics={
                "aqi": 185,
                "temperature": 39,
                "green_cover": 14,
                "carbon_emissions": 50,
                "health_risk": 60,
                "population_exposure": 1000,
                "cost": 1000,
            }
        ),
    )

    result = run_simulation(request)
    repeated = run_simulation(request)

    assert result.baseline_state.aqi == 185
    assert result.simulated_state.aqi == 175
    assert result.metrics["aqi"].absolute_delta == -10
    assert result.metrics["aqi"].percentage_delta == -10 / 185 * 100
    assert result.simulated_state.temperature == 37.5
    assert result.simulated_state.green_cover == 16
    assert result.simulated_state.carbon_emissions == 47
    assert result.simulated_state.health_risk == 58
    assert result.simulated_state.cost == 5000
    assert result.metrics["population_exposure"].availability == "unavailable"
    assert result.metadata.reproducibility_key == repeated.metadata.reproducibility_key
    assert result.metrics == repeated.metrics


def test_business_as_usual_uses_digital_twin_baseline_without_inventing_metrics() -> None:
    from app.digital_twin.service import get_ward_state

    ward = get_ward_state(80)
    baseline_scenario = Scenario(
        scenario_id="scenario-bau-ward-80",
        name="Business as Usual",
        description="No new intervention.",
        city="Delhi",
        zone="Ward_80",
        intervention_type="baseline",
    )
    result = run_simulation(SimulationRequest(
        urban_state=UrbanState(
            workflow_id="bau-ward-80",
            request={"query": "Baseline", "city": "Delhi", "zone": "Ward_80"},
        ),
        scenario=baseline_scenario,
    ))

    for metric in ("aqi", "temperature", "green_cover", "health_risk"):
        expected = ward[metric]
        assert result.metrics[metric].baseline_value == expected
        assert result.metrics[metric].simulated_value == expected
        assert result.metrics[metric].absolute_delta == 0
        assert result.metrics[metric].availability == "available"
        assert "Phase 5 Digital Twin" in result.metrics[metric].source_model
    assert result.metrics["carbon_emissions"].simulated_value is None
    assert result.metrics["carbon_emissions"].availability_reason
    assert result.metrics["population_exposure"].simulated_value is None
    assert "not exposed population" in result.metrics["population_exposure"].availability_reason


def test_intervention_simulation_reports_baseline_and_unavailable_effects() -> None:
    intervention_scenario = Scenario(
        scenario_id="scenario-forest-ward-80",
        name="Urban Forest Expansion",
        description="Candidate urban forest expansion.",
        city="Delhi",
        zone="Ward_80",
        intervention_type="green_infrastructure",
        interventions=[
            ScenarioIntervention(
                intervention_id="urban_forest_expansion",
                name="Urban Forest Expansion",
                parameters={"area_hectares": 2, "tree_density": 100},
            )
        ],
    )
    result = run_simulation(SimulationRequest(
        urban_state=UrbanState(
            workflow_id="forest-ward-80",
            request={"query": "Increase green cover", "city": "Delhi", "zone": "Ward_80"},
        ),
        scenario=intervention_scenario,
    ))

    assert result.metrics["aqi"].baseline_value is not None
    assert result.metrics["aqi"].simulated_value is None
    assert result.metrics["aqi"].availability == "unavailable"
    assert "No validated intervention-to-model-feature mapping" in result.metrics["aqi"].availability_reason
    assert result.metrics["green_cover"].baseline_value is not None
    assert result.metrics["green_cover"].simulated_value is None
    assert result.metrics["carbon_impact"].baseline_value is None
    assert result.metrics["carbon_impact"].simulated_value is None
    assert result.metrics["cost"].simulated_value is None
    assert all(
        result.metrics[metric].availability_reason
        for metric in ("green_cover", "carbon_impact", "cost", "sustainability")
    )

    response = client.post(
        "/api/v1/scenarios/simulate",
        json={
            "scenario": intervention_scenario.model_dump(mode="json"),
            "urban_state": {
                "workflow_id": "forest-ward-80-api",
                "request": {
                    "query": "Increase green cover",
                    "city": "Delhi",
                    "zone": "Ward_80",
                },
            },
            "simulation_input": {"baseline_metrics": {}},
        },
    )
    assert response.status_code == 200, response.text
    response_metrics = response.json()["metrics"]
    assert response_metrics["aqi"]["baseline_value"] == result.metrics["aqi"].baseline_value
    assert response_metrics["aqi"]["simulated_value"] is None
    assert response_metrics["aqi"]["availability_reason"]


def test_partial_simulation_keeps_provenance_backed_estimates_and_reasons() -> None:
    scenario = _scenario()
    request = SimulationRequest(
        urban_state=_state(),
        scenario=scenario,
        simulation_input=SimulationInput(
            baseline_metrics={"aqi": 100},
            scenario_estimates={
                "aqi": ScenarioMetricEstimate(
                    value=92,
                    unit="AQI",
                    source_type="external_simulator",
                    source="validated test simulator output",
                    model_name="test-air-quality-simulator",
                    model_version="test-v1",
                )
            },
        ),
    )

    result = run_simulation(request)

    assert result.metrics["aqi"].simulated_value == 92
    assert result.metrics["aqi"].absolute_delta == -8
    assert result.metrics["aqi"].source_model == "test-air-quality-simulator (test-v1)"
    assert result.metrics["green_cover"].simulated_value is None
    assert result.metrics["green_cover"].availability == "unavailable"
    assert result.metrics["green_cover"].availability_reason
    assert result.metrics["cost"].simulated_value == 5000


def test_external_simulation_estimates_retain_provenance_and_uncertainty() -> None:
    request = SimulationRequest(
        urban_state=_state(),
        scenario=_scenario(),
        simulation_input=SimulationInput(
            baseline_metrics={"population_exposure": 1000, "sustainability": 0.4},
            scenario_estimates={
                "population_exposure": ScenarioMetricEstimate(
                    value=800,
                    unit="people",
                    source_type="external_simulator",
                    source="exposure model run 17",
                    model_name="exposure-model",
                    model_version="v2",
                    uncertainty=25,
                ),
                "sustainability": ScenarioMetricEstimate(
                    value=0.7,
                    unit="score",
                    source_type="validated_model",
                    source="sustainability scorer",
                    confidence=0.8,
                ),
            },
        ),
    )

    result = run_simulation(request)

    assert result.metrics["population_exposure"].absolute_delta == -200
    assert result.metrics["population_exposure"].uncertainty == 25
    assert result.metrics["population_exposure"].source_model == "exposure-model (v2)"
    assert result.metrics["sustainability"].simulated_value == 0.7
    assert result.metrics["sustainability"].confidence == 0.8


def test_optimization_respects_directions_constraints_and_pareto_frontier() -> None:
    first = _simulation("first", cost=10, green=20)
    second = _simulation("second", cost=20, green=30)
    dominated = _simulation("dominated", cost=30, green=10)
    request = OptimizationRequest(
        simulations=[first, second, dominated],
        objectives=[
            ObjectiveDefinition(name="cost", direction="minimize"),
            ObjectiveDefinition(name="green_cover", direction="maximize"),
        ],
        constraints=[
            ConstraintDefinition(name="budget", metric="cost", operator="<=", value=40)
        ],
    )

    result = run_optimization(request)

    assert {item.scenario_id for item in result.pareto_solutions} == {"first", "second"}
    assert [item.scenario_id for item in result.dominated_strategies] == ["dominated"]
    assert result.infeasible_strategies == []
    assert "crowding_boundary" in result.model_dump_json()
    constrained = run_optimization(request.model_copy(update={
        "constraints": [
            ConstraintDefinition(name="budget", metric="cost", operator="<=", value=15)
        ]
    }))
    assert [item.scenario_id for item in constrained.infeasible_strategies] == ["second", "dominated"]
    assert [item.scenario_id for item in constrained.pareto_solutions] == ["first"]


def test_prediction_explanation_uses_shap_and_counterfactual_changes_one_feature() -> None:
    with AQI_MODEL_INFO_PATH.open("r", encoding="utf-8") as handle:
        feature_names = json.load(handle)["features"]
    features = {name: 1.0 for name in feature_names}

    explanation = explain_prediction(ExplanationRequest(model_name="aqi", features=features))
    counterfactual = run_counterfactual(CounterfactualRequest(
        model_name="aqi",
        features=features,
        feature_name="pm10",
        counterfactual_value=2.0,
    ))

    assert explanation.explanation_method == "TreeExplainer"
    assert "sha256:" in explanation.model_version
    assert explanation.prediction is not None
    assert explanation.confidence is None
    assert explanation.feature_contributions
    assert counterfactual.baseline_feature_value == 1.0
    assert counterfactual.counterfactual_feature_value == 2.0
    assert counterfactual.absolute_delta == (
        counterfactual.counterfactual_prediction - counterfactual.baseline_prediction
    )
    with pytest.raises(ValueError, match="not used by the"):
        run_counterfactual(CounterfactualRequest(
            model_name="aqi",
            features={**features, "unrecognized_feature": 1.0},
            feature_name="unrecognized_feature",
            counterfactual_value=2.0,
        ))


def test_formula_model_explanation_uses_supplied_shap_background() -> None:
    with GREEN_COVER_MODEL_INFO_PATH.open("r", encoding="utf-8") as handle:
        feature_names = json.load(handle)["features"]
    features = {name: 0.1 for name in feature_names}
    background = [
        {name: 0.0 for name in feature_names},
        {name: 0.05 for name in feature_names},
    ]

    explanation = explain_prediction(ExplanationRequest(
        model_name="green_cover",
        features=features,
        background_features=background,
    ))

    assert explanation.explanation_method == "PermutationExplainer"
    assert explanation.feature_contributions


def test_simulation_and_optimization_results_persist(tmp_path, monkeypatch) -> None:
    from app.phase11 import repository as simulation_repository
    from app.phase12 import repository as optimization_repository

    test_engine = create_engine(f"sqlite:///{tmp_path / 'phase11-13.sqlite3'}")
    Base.metadata.create_all(test_engine)
    session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    for repository in (simulation_repository, optimization_repository):
        monkeypatch.setattr(repository, "SessionLocal", session_factory)
        monkeypatch.setattr(repository, "initialize_database", lambda: Base.metadata.create_all(test_engine))

    simulation = _simulation("persisted", cost=100, green=20)
    simulation_repository.persist_simulation(simulation)
    assert simulation_repository.get_simulation(simulation.simulation_id)["scenario_id"] == "persisted"

    optimization = run_optimization(OptimizationRequest(
        simulations=[simulation],
        objectives=[ObjectiveDefinition(name="green_cover", direction="maximize")],
    ))
    optimization_repository.persist_optimization(optimization)
    assert optimization_repository.get_optimization(optimization.optimization_id)["status"] == "completed"


def test_simulation_and_optimization_http_run_and_retrieve(monkeypatch) -> None:
    from app.phase11 import api as simulation_api
    from app.phase12 import api as optimization_api

    monkeypatch.setattr(simulation_api, "persist_simulation", lambda _: None)
    simulation_response = client.post(
        "/api/v1/simulation/run",
        json=SimulationRequest(
            urban_state=_state(),
            scenario=_scenario(),
            simulation_input=SimulationInput(baseline_metrics={"aqi": 100}),
        ).model_dump(mode="json"),
    )
    assert simulation_response.status_code == 200, simulation_response.text
    simulation_data = simulation_response.json()
    monkeypatch.setattr(simulation_api, "get_simulation", lambda _: simulation_data)
    assert client.get(f"/api/v1/simulation/{simulation_data['simulation_id']}").status_code == 200

    monkeypatch.setattr(optimization_api, "persist_optimization", lambda _: None)
    optimization_response = client.post(
        "/api/v1/optimization/run",
        json={
            "simulations": [simulation_data],
            "objectives": [{"name": "aqi", "direction": "minimize"}],
        },
    )
    assert optimization_response.status_code == 200, optimization_response.text
    optimization_data = optimization_response.json()
    monkeypatch.setattr(optimization_api, "get_optimization", lambda _: optimization_data)
    assert client.get(
        f"/api/v1/optimization/{optimization_data['optimization_id']}"
    ).status_code == 200
    pareto_response = client.get(
        f"/api/v1/optimization/{optimization_data['optimization_id']}/pareto"
    )
    assert pareto_response.status_code == 200, pareto_response.text
    assert pareto_response.json()["pareto_solutions"] == optimization_data["pareto_solutions"]


def test_end_to_end_scenario_simulation_optimization_explanation_and_api_routes(monkeypatch) -> None:
    monkeypatch.setattr(pipeline_module, "persist_scenario_set", lambda _: None)
    monkeypatch.setattr(pipeline_module, "persist_simulation", lambda _: None)
    monkeypatch.setattr(pipeline_module, "persist_optimization", lambda _: None)
    request = PipelineRequest(
        city="TestCity",
        zone="Ward 1",
        problem_statement="Low green cover",
        problems=["low_green_cover"],
        requested_interventions=["Urban Forest Expansion"],
        intervention_parameters={
            "urban_forest_expansion": {"area_hectares": 2, "tree_density": 100}
        },
        simulation_input=SimulationInput(
            model_features={
                "green_cover": {
                    "trees": 0.1,
                    "grass": 0.0,
                    "flooded_vegetation": 0.0,
                    "crops": 0.0,
                    "shrub_and_scrub": 0.0,
                    "vegetation": 0.1,
                    "built": 0.5,
                }
            },
            scenario_features_by_intervention={
                "urban_forest_expansion": {
                    "green_cover": {
                        "trees": 0.2,
                        "vegetation": 0.2,
                        "built": 0.5,
                    }
                }
            },
        ),
        optimization_objectives=[
            ObjectiveDefinition(name="green_cover", direction="maximize", weight=1)
        ],
    )

    response = client.post("/api/v1/pipeline/run", json=request.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    result = PipelineResult.model_validate(response.json())

    assert result.scenarios
    assert result.simulations
    assert result.optimization is not None
    assert result.explanation is not None
    assert result.final_report["pareto_scenario_ids"]
    assert result.final_report["pareto_strategies"]
    by_scenario = {item.scenario_id: item for item in result.simulations}
    forest_scenario = next(item for item in result.scenarios if item.name == "Urban Forest Expansion")
    assert by_scenario[forest_scenario.scenario_id].metrics["green_cover"].simulated_value == 31
    assert result.explanation.strategy_explanations[0].reasons
    paths = app.openapi()["paths"]
    assert "/api/v1/simulation/run" in paths
    assert "get" in paths["/api/v1/simulation/{simulation_id}"]
    assert "/api/v1/optimization/run" in paths
    assert "get" in paths["/api/v1/optimization/{optimization_id}"]
    assert "get" in paths["/api/v1/optimization/{optimization_id}/pareto"]
    assert "/api/v1/explain/prediction" in paths
    assert "/api/v1/explain/recommendation" in paths
    assert "/api/v1/explain/counterfactual" in paths
    assert "/api/v1/pipeline/run" in paths
