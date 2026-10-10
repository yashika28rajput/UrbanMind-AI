"""Regression tests: scenario persistence over real HTTP + isolated DB, plus security guards."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.phase10 import repository
from app.phase10.engine import generate_scenario_set
from app.phase10.schemas import ScenarioGenerationRequest
from app.phase9.graph.state import UrbanState

client = TestClient(app)

GENERATE = {
    "city": "TestCity",
    "zone": "RegressionZone",
    "problem_statement": "High PM2.5 and low green cover",
    "problems": ["high_pm25", "low_green_cover"],
    "requested_interventions": ["Urban Forest Expansion"],
    "intervention_parameters": {"urban_forest_expansion": {"area_hectares": 5, "tree_density": 300}},
    "max_scenarios": 4,
}


def _generated_set():
    state = UrbanState(workflow_id="reg", request={"query": "x", "city": "TestCity", "zone": "RegressionZone"})
    return generate_scenario_set(state, ScenarioGenerationRequest(**GENERATE))


def test_generated_scenarios_are_persisted_and_retrievable_over_http() -> None:
    response = client.post("/api/v1/scenarios/generate", json=GENERATE)
    assert response.status_code == 200, response.text
    scenarios = response.json()["scenarios"]
    assert scenarios
    for item in scenarios:
        fetched = client.get(f"/api/v1/scenarios/{item['scenario_id']}")
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["request_id"] == response.json()["request_id"]


def test_storing_same_request_twice_is_a_409_conflict_not_a_storage_outage() -> None:
    scenario_set = _generated_set()
    repository.persist_scenario_set(scenario_set)
    with pytest.raises(repository.ScenarioConflictError):
        repository.persist_scenario_set(scenario_set)


def test_failed_set_insert_leaves_no_orphan_rows() -> None:
    scenario_set = _generated_set()
    duplicate = scenario_set.model_copy(deep=True)
    duplicate.scenarios = [scenario_set.scenarios[0], scenario_set.scenarios[0]]  # PK clash inside the set
    with pytest.raises(Exception):
        repository.persist_scenario_set(duplicate)
    with repository.SessionLocal() as session:
        assert session.get(repository.ScenarioRequestRecord, duplicate.request_id) is None


def test_version_for_missing_parent_request_is_rejected_without_touching_fk() -> None:
    scenario = _generated_set().scenarios[0]
    with pytest.raises(repository.ScenarioParentMissingError):
        repository.persist_scenario_version("does-not-exist", scenario)


def test_duplicate_version_write_is_conflict() -> None:
    scenario_set = _generated_set()
    repository.persist_scenario_set(scenario_set)
    with pytest.raises(repository.ScenarioConflictError):
        repository.persist_scenario_version(scenario_set.request_id, scenario_set.scenarios[0])


@pytest.mark.parametrize("name", ["../../escape", "a/b", "..", "x" * 65, ""])
def test_federated_model_name_cannot_traverse_paths(name) -> None:
    response = client.post("/api/v1/federated/start", json={"model_name": name, "num_rounds": 1, "num_clients": 2})
    assert response.status_code == 422


def test_cors_does_not_reflect_arbitrary_origins() -> None:
    response = client.options(
        "/api/v1/scenarios",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"
    assert response.headers.get("access-control-allow-origin") != "*"
    allowed = client.options(
        "/api/v1/scenarios",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
