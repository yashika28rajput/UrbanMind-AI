from fastapi.testclient import TestClient

from app.main import app
from app.phase9.graph.workflow import analyze_urban_problem

client = TestClient(app)


def test_phase9_analysis_workflow_runs() -> None:
    result = analyze_urban_problem({
        "query": "Delhi Zone X has high PM2.5 and high population exposure.",
        "city": "Delhi",
        "zone": "Zone X",
        "requested_interventions": ["Green Infrastructure", "Public Transport Improvement"],
    })

    assert result.workflow_status == "completed"
    assert result.final_report is not None
    assert result.final_report.executive_summary
    assert result.optimization_results is not None
    assert result.critic_results is not None


def test_phase9_http_endpoint_smoke() -> None:
    response = client.post(
        "/api/v1/agentic/analyze",
        json={
            "query": "Delhi Zone X has high PM2.5 and high population exposure.",
            "city": "Delhi",
            "zone": "Zone X",
            "requested_interventions": ["Green Infrastructure", "Public Transport Improvement"],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["interventions"]
    assert payload["critic"]["critic_status"] == "passed"
