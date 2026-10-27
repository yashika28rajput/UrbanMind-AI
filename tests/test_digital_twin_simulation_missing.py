import asyncio

from app.api import digital_twin as digital_twin_api


def test_simulation_keeps_missing_metrics_unavailable_when_adjusted(monkeypatch) -> None:
    model = {
        "city": "Delhi",
        "phase": "test",
        "digital_twin_type": "virtual_city_model",
        "summary": {},
    }
    monkeypatch.setattr(digital_twin_api, "get_virtual_city_model", lambda: model)
    result = asyncio.run(digital_twin_api.digital_twin_simulate(
        {
            "baseline_state": {
                "aqi": None,
                "temperature": 30.0,
                "population": 0,
                "green_cover": "not numeric",
                "health_risk": float("nan"),
                "traffic_density": 1e308,
                "cost": 20,
            },
            "adjustments": {
                "aqi": 25,
                "temperature": -2,
                "population": 100,
                "green_cover": 5,
                "health_risk": 1,
                "traffic_density": 1e308,
                "cost": "5",
            },
        }
    ))
    assert result["simulated_state"]["aqi"] is None
    assert result["metric_changes"]["aqi"]["baseline"] is None
    assert result["metric_changes"]["aqi"]["simulated"] is None
    assert result["metric_changes"]["aqi"]["delta"] is None
    assert result["simulated_state"]["temperature"] == 28
    assert result["metric_changes"]["temperature"]["delta"] == -2
    assert result["simulated_state"]["population"] == 100
    assert result["simulated_state"]["green_cover"] is None
    assert result["metric_changes"]["green_cover"]["delta"] is None
    assert result["simulated_state"]["health_risk"] is None
    assert result["metric_changes"]["health_risk"]["delta"] is None
    assert result["simulated_state"]["traffic_density"] == 1e308
    assert result["metric_changes"]["traffic_density"]["delta"] == 0
    assert result["simulated_state"]["cost"] == 20
