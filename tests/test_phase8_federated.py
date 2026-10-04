import numpy as np
from fastapi.testclient import TestClient

from app.federated.aggregation import fedavg_aggregate
from app.federated.model_adapter import AQIModelAdapter
from app.main import app

client = TestClient(app)


def test_fedavg_weighted_aggregation() -> None:
    aggregated = fedavg_aggregate([np.array([2.0]), np.array([4.0])], [100, 300])
    assert np.allclose(aggregated, np.array([3.5]))


def test_model_adapter_round_trip() -> None:
    adapter = AQIModelAdapter()
    model = adapter.create_model()
    parameters = adapter.get_parameters(model)
    restored = adapter.set_parameters(adapter.create_model(), parameters)
    assert np.allclose(adapter.get_parameters(restored), parameters)


def test_federated_start_endpoint_smoke() -> None:
    response = client.post(
        "/api/v1/federated/start",
        json={"num_rounds": 1, "num_clients": 2, "local_epochs": 1, "model_name": "aqi_model"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "completed"
    assert "global_metrics" in payload
    assert "city_metrics" in payload
