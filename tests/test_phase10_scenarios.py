from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
import pytest

from app.api import scenarios as scenarios_api
from app.main import app
from app.phase10.engine import generate_scenario_set
from app.phase10 import repository
from app.phase10.schemas import CostEstimate, ImpactEstimate, Scenario, ScenarioGenerationRequest
from app.database.urban_memory_store import Base
from app.phase9.graph.state import UrbanState

client = TestClient(app)


def scenario_test_engine(database_path):
    test_engine = create_engine(f"sqlite:///{database_path}")

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    return test_engine


def urban_state(query: str = "High PM2.5 and low green cover in TestCity.") -> UrbanState:
    return UrbanState(
        workflow_id="test-workflow",
        request={"query": query, "city": "TestCity", "zone": "TestZone"},
    )


def test_scenario_generation_returns_baseline_options_without_fake_estimates() -> None:
    request = ScenarioGenerationRequest(
        city="TestCity",
        zone="TestZone",
        problem_statement="High PM2.5 and low green cover",
        problems=["high_pm25", "low_green_cover"],
        requested_interventions=["Urban Forest Expansion", "Electric Bus Deployment"],
        intervention_parameters={
            "urban_forest_expansion": {"area_hectares": 12, "tree_density": 300},
            "electric_bus_deployment": {"number_of_buses": 20, "deployment_period_years": 2},
        },
        max_scenarios=6,
    )
    result = generate_scenario_set(urban_state(), request)
    payload = result.model_dump(mode="json")

    assert result.identified_problems == ["high_pm25", "low_green_cover"]
    assert result.scenarios[0].name == "Business as Usual"
    assert any(len(scenario.interventions) == 2 for scenario in result.scenarios)
    assert all(scenario.expected_impacts is None for scenario in result.scenarios)
    assert all(scenario.estimated_cost is None for scenario in result.scenarios)
    assert all(
        "emission_pressure_index" in scenario.carbon_reduction_availability_reason
        for scenario in result.scenarios
    )
    assert all(
        set(intervention.parameters) == set(intervention.parameter_sources)
        for scenario in result.scenarios
        for intervention in scenario.interventions
    )
    assert all(item["scenario_id"] for item in payload["scenarios"])
    assert all(
        scenario.status != "SIMULATION_READY"
        or all(intervention.parameters for intervention in scenario.interventions)
        for scenario in result.scenarios
    )


def test_planner_schedule_is_preserved_for_intervention_scenarios() -> None:
    result = generate_scenario_set(
        urban_state("Low green cover in TestCity."),
        ScenarioGenerationRequest(
            city="TestCity",
            problem_statement="Low green cover",
            problems=["low_green_cover"],
            requested_interventions=["Urban Forest Expansion"],
            implementation_period_years=2.75,
        ),
    )

    forest = next(item for item in result.scenarios if item.name == "Urban Forest Expansion")
    assert forest.provenance["implementation_schedule"] == {
        "duration_years": 2.75,
        "source_type": "user_input",
        "source": "Planner-supplied implementation schedule",
    }
    assert forest.expected_impacts is None
    assert forest.estimated_cost is None


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf"), float("-inf")])
def test_scenario_generation_rejects_invalid_planner_durations(duration: float) -> None:
    with pytest.raises(ValidationError, match="implementation_period_years"):
        ScenarioGenerationRequest(
            city="TestCity",
            problem_statement="Low green cover",
            implementation_period_years=duration,
        )


def test_missing_parameters_and_budget_are_not_claimed_feasible() -> None:
    result = generate_scenario_set(
        urban_state("High PM2.5 in TestCity."),
        ScenarioGenerationRequest(
            city="TestCity",
            problem_statement="High PM2.5",
            requested_interventions=["Electric Bus Deployment"],
            constraints={"budget_limit": 1000000},
        ),
    )

    electric_bus = next(item for item in result.scenarios if item.intervention_type == "public_transport")
    assert electric_bus.status == "REQUIRES_REVIEW"
    assert "number_of_buses" in " ".join(electric_bus.constraints)
    assert "Budget feasibility cannot be verified" in " ".join(electric_bus.constraints)


def test_scenario_lab_problem_text_matches_requested_catalog_interventions() -> None:
    problem = (
        "Chandni Chowk has high air pollution, limited green cover and heat stress, "
        "creating environmental and public health risks."
    )
    requested_interventions = [
        "Urban Forest Expansion",
        "Green Roof Program",
        "Electric Bus Deployment",
    ]
    result = generate_scenario_set(
        urban_state(problem),
        ScenarioGenerationRequest(
            city="Delhi",
            zone="Ward_80",
            problem_statement=problem,
            problems=[problem],
            objectives=[
                "Reduce air pollution",
                "Improve green cover",
                "Reduce heat stress",
                "Improve public health",
            ],
            requested_interventions=requested_interventions,
        ),
    )

    generated_names = {scenario.name for scenario in result.scenarios}
    assert {
        "Business as Usual",
        *requested_interventions,
    } <= generated_names
    assert {"high_aqi", "low_green_cover", "high_uhi"} <= set(result.identified_problems)
    assert all(scenario.expected_impacts is None for scenario in result.scenarios)
    assert all(scenario.estimated_cost is None for scenario in result.scenarios)
    assert [item.requested_name for item in result.intervention_diagnostics] == requested_interventions
    assert all(item.matched and not item.rejected for item in result.intervention_diagnostics)
    assert all("requires review" in item.reason.lower() for item in result.intervention_diagnostics)
    for diagnostic in result.intervention_diagnostics:
        assert diagnostic.canonical_intervention_id


def test_validator_rejects_invalid_cost_ranges() -> None:
    try:
        CostEstimate(min_cost=10, max_cost=1)
    except ValidationError:
        return
    raise AssertionError("invalid cost range should be rejected")


def test_numeric_estimates_require_provenance() -> None:
    for create_estimate in (
        lambda: CostEstimate(total_estimated_cost=100),
        lambda: ImpactEstimate(expected_aqi_change=-5),
    ):
        try:
            create_estimate()
        except ValidationError:
            continue
        raise AssertionError("an estimate without provenance should be rejected")


def test_known_land_limit_marks_scenario_invalid_and_aliases_deduplicate() -> None:
    result = generate_scenario_set(
        urban_state("Low green cover in TestCity."),
        ScenarioGenerationRequest(
            city="TestCity",
            problem_statement="Low green cover",
            problems=["low_green_cover"],
            requested_interventions=["Urban Forest Expansion", "tree plantation"],
            intervention_parameters={
                "urban_forest_expansion": {"area_hectares": 12, "tree_density": 300},
            },
            constraints={"available_land_hectares": 10},
        ),
    )

    forests = [
        item for item in result.scenarios
        if any(intervention.intervention_id == "urban_forest_expansion" for intervention in item.interventions)
        and len(item.interventions) == 1
    ]
    assert len(forests) == 1
    assert forests[0].status == "INVALID"
    assert "exceeds available land" in " ".join(forests[0].constraints)


def test_phase10_http_generation_and_retrieval(monkeypatch) -> None:
    monkeypatch.setattr(scenarios_api, "persist_scenario_set", lambda _: None)
    response = client.post(
        "/api/v1/scenarios/generate",
        json={
            "city": "TestCity",
            "zone": "TestZone",
            "problem_statement": "High PM2.5",
            "problems": ["high_pm25"],
            "requested_interventions": ["Electric Bus Deployment"],
            "intervention_parameters": {
                "electric_bus_deployment": {
                    "number_of_buses": 10,
                    "deployment_period_years": 2,
                }
            },
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["request_id"]
    assert payload["scenarios"][0]["name"] == "Business as Usual"
    electric_bus = next(
        scenario for scenario in payload["scenarios"]
        if scenario["name"] == "Electric Bus Deployment"
    )
    scenario_id = electric_bus["scenario_id"]
    monkeypatch.setattr(
        scenarios_api,
        "get_scenario",
        lambda requested_id, version=None: (
            {**electric_bus, "request_id": payload["request_id"]}
            if requested_id == scenario_id
            else None
        ),
    )
    retrieval = client.get(f"/api/v1/scenarios/{scenario_id}")
    assert retrieval.status_code == 200, retrieval.text
    assert retrieval.json()["name"] == "Electric Bus Deployment"
    monkeypatch.setattr(scenarios_api, "persist_scenario_version", lambda *_: None)
    version_response = client.post(
        f"/api/v1/scenarios/{scenario_id}/versions",
        json={"parameter_updates": {"electric_bus_deployment": {"number_of_buses": 15}}},
    )
    assert version_response.status_code == 200, version_response.text
    assert version_response.json()["scenario_id"] == scenario_id
    assert version_response.json()["scenario_version"] == 2
    assert version_response.json()["interventions"][0]["parameters"]["number_of_buses"] == 15

    electric_bus["status"] = "SIMULATED"
    simulated_version = client.post(
        f"/api/v1/scenarios/{scenario_id}/versions",
        json={"parameter_updates": {"electric_bus_deployment": {"number_of_buses": 18}}},
    )
    assert simulated_version.status_code == 200, simulated_version.text
    assert simulated_version.json()["status"] == "REQUIRES_REVIEW"
    assert electric_bus["status"] == "SIMULATED"


def test_phase10_http_accepts_scenario_lab_problem_text(monkeypatch) -> None:
    monkeypatch.setattr(scenarios_api, "persist_scenario_set", lambda _: None)
    problem = (
        "Chandni Chowk has high air pollution, limited green cover and heat stress, "
        "creating environmental and public health risks."
    )
    requested = [
        "Urban Forest Expansion",
        "Green Roof Program",
        "Electric Bus Deployment",
    ]
    response = client.post(
        "/api/v1/scenarios/generate",
        json={
            "city": "Delhi",
            "zone": "Ward_80",
            "problem_statement": problem,
            "problems": [problem],
            "objectives": [
                "Reduce air pollution",
                "Improve green cover",
                "Reduce heat stress",
                "Improve public health",
            ],
            "requested_interventions": requested,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert {
        "Business as Usual",
        *requested,
    } <= {scenario["name"] for scenario in payload["scenarios"]}
    assert {item["canonical_intervention_id"] for item in payload["intervention_diagnostics"]} == {
        "urban_forest_expansion",
        "green_roof_program",
        "electric_bus_deployment",
    }


def test_generation_requires_urban_problem() -> None:
    response = client.post("/api/v1/scenarios/generate", json={"city": "TestCity"})
    assert response.status_code == 422


def test_scenario_persistence_round_trip(tmp_path, monkeypatch) -> None:
    test_engine = scenario_test_engine(tmp_path / "scenario-test.sqlite3")
    monkeypatch.setattr(repository, "SessionLocal", sessionmaker(bind=test_engine, expire_on_commit=False))
    monkeypatch.setattr(repository, "initialize_database", lambda: Base.metadata.create_all(test_engine))
    generated = generate_scenario_set(
        urban_state("Karol Bagh has high air pollution and insufficient green cover."),
        ScenarioGenerationRequest(
            city="Delhi",
            zone="Ward_91",
            problem_statement=(
                "Karol Bagh has high air pollution and insufficient green cover, "
                "creating environmental and public health risks."
            ),
            objectives=[
                "Reduce air pollution",
                "Improve green cover",
                "Reduce heat stress",
                "Improve public health",
            ],
            requested_interventions=[
                "Urban Forest Expansion",
                "Green Roof Program",
                "Electric Bus Deployment",
            ],
        ),
    )
    request_id = generated.request_id

    repository.persist_scenario_set(generated)

    assert generated.request_id == request_id
    assert repository.ScenarioRequestRecord.__table__.primary_key.columns.keys() == ["request_id"]
    assert (
        next(iter(repository.ScenarioRecord.__table__.c.request_id.foreign_keys)).target_fullname
        == "scenario_requests.request_id"
    )
    with repository.SessionLocal() as session:
        parent = session.get(repository.ScenarioRequestRecord, request_id)
        persisted_scenarios = (
            session.query(repository.ScenarioRecord)
            .filter_by(request_id=request_id)
            .all()
        )
        all_request_ids = {
            row.request_id
            for row in session.query(repository.ScenarioRecord).all()
        }
    assert parent is not None
    assert len(persisted_scenarios) == len(generated.scenarios)
    assert all(row.request_id == request_id for row in persisted_scenarios)
    assert all_request_ids == {request_id}
    assert repository.get_scenario(generated.scenarios[0].scenario_id)["name"] == "Business as Usual"
    original = generated.scenarios[1]
    revised = original.model_copy(deep=True)
    revised.scenario_version = 2
    repository.persist_scenario_version(generated.request_id, revised)
    assert repository.get_scenario(original.scenario_id)["scenario_version"] == 2
    assert repository.get_scenario(original.scenario_id, version=1)["scenario_version"] == 1
    listed = repository.list_scenarios(city="Delhi", zone="Ward_91")
    assert len(listed) == len(generated.scenarios) + 1
    assert {scenario["request_id"] for scenario in listed} == {generated.request_id}
    test_engine.dispose()


def test_scenario_set_persistence_rolls_back_parent_when_child_insert_fails(
    tmp_path, monkeypatch
) -> None:
    test_engine = scenario_test_engine(tmp_path / "scenario-rollback.sqlite3")
    monkeypatch.setattr(repository, "SessionLocal", sessionmaker(bind=test_engine, expire_on_commit=False))
    monkeypatch.setattr(repository, "initialize_database", lambda: Base.metadata.create_all(test_engine))
    generated = generate_scenario_set(
        urban_state("High air pollution in Delhi."),
        ScenarioGenerationRequest(
            city="Delhi",
            zone="Ward_91",
            problem_statement="High air pollution",
            problems=["high_pm25"],
            requested_interventions=["Electric Bus Deployment"],
        ),
    )
    with test_engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TRIGGER reject_scenario_insert
            BEFORE INSERT ON scenarios
            BEGIN
                SELECT RAISE(ABORT, 'forced scenario insert failure');
            END
            """
        )

    with pytest.raises(IntegrityError):
        repository.persist_scenario_set(generated)

    with repository.SessionLocal() as session:
        assert session.get(repository.ScenarioRequestRecord, generated.request_id) is None
        assert session.query(repository.ScenarioRecord).count() == 0

    test_engine.dispose()
