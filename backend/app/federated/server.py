from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
from flwr.common import ndarrays_to_parameters, parameters_to_ndarrays
from flwr.server import ServerConfig
from flwr.server.strategy import FedAvg
from flwr.simulation import start_simulation

from .aggregation import fedavg_aggregate
from .client import make_client_fn
from .config import SETTINGS
from .model_adapter import AQIModelAdapter

logger = logging.getLogger(__name__)
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
current_pythonpath = os.environ.get("PYTHONPATH", "")
entries = [str(backend_dir)] + ([current_pythonpath] if current_pythonpath else [])
os.environ["PYTHONPATH"] = os.pathsep.join(part for part in entries if part)

FEDERATED_STATUS: dict[str, object] = {
    "status": "IDLE",
    "current_round": 0,
    "total_rounds": SETTINGS.num_rounds,
    "connected_clients": 0,
    "participating_clients": 0,
    "training_loss": None,
    "metrics": {},
    "start_time": None,
    "completion_time": None,
    "error": None,
    "model_name": SETTINGS.model_name,
    "model_version": SETTINGS.model_version,
}


class FederatedAveragingStrategy(FedAvg):
    def __init__(self, *, initial_parameters=None, **kwargs):
        super().__init__(**kwargs)
        self.initial_parameters = initial_parameters
        self.last_aggregated_parameters = None

    def initialize_parameters(self, client_manager):
        if self.initial_parameters is not None:
            return self.initial_parameters
        return super().initialize_parameters(client_manager)

    def aggregate_fit(self, server_round, results, failures):
        FEDERATED_STATUS["status"] = "AGGREGATING"
        FEDERATED_STATUS["current_round"] = int(server_round)
        if not results:
            return None, {}

        parameter_arrays = []
        sample_counts = []
        for _, fit_res in results:
            if fit_res.parameters is None:
                continue
            arrays = parameters_to_ndarrays(fit_res.parameters)
            if not arrays:
                continue
            parameter_arrays.append(np.asarray(arrays[0], dtype=float))
            sample_counts.append(int(fit_res.num_examples))

        if not parameter_arrays:
            return None, {}

        aggregated = fedavg_aggregate(parameter_arrays, sample_counts)
        self.last_aggregated_parameters = aggregated
        FEDERATED_STATUS["participating_clients"] = len(results)
        FEDERATED_STATUS["metrics"] = {
            "round": int(server_round),
            "clients": len(results),
            "n_samples": int(sum(sample_counts)),
        }
        return ndarrays_to_parameters([aggregated]), {}


def _save_checkpoint(model_name: str, round_number: int, parameters: np.ndarray) -> Path:
    model_dir = Path(__file__).resolve().parents[3] / "models" / "federated" / model_name
    model_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = model_dir / f"round_{round_number:03d}.npz"
    np.savez(checkpoint_path, parameters=parameters)
    return checkpoint_path


def run_federated_simulation(*, num_rounds: int = None, num_clients: int = 3, local_epochs: int = None, model_name: str = None) -> dict[str, object]:
    rounds = int(num_rounds or SETTINGS.num_rounds)
    clients = int(num_clients or 3)
    epochs = int(local_epochs or SETTINGS.local_epochs)
    model_name = model_name or SETTINGS.model_name

    adapter = AQIModelAdapter(model_name=model_name)
    initial_model = adapter.create_model()
    initial_parameters = [adapter.get_parameters(initial_model)]

    strategy = FederatedAveragingStrategy(
        initial_parameters=ndarrays_to_parameters([initial_parameters[0]]),
        fraction_fit=1.0,
        min_fit_clients=clients,
        min_available_clients=clients,
        on_fit_config_fn=lambda server_round: {"local_epochs": epochs, "round": server_round},
    )

    FEDERATED_STATUS.update(
        {
            "status": "INITIALIZING",
            "current_round": 0,
            "total_rounds": rounds,
            "connected_clients": clients,
            "participating_clients": 0,
            "training_loss": None,
            "metrics": {},
            "start_time": None,
            "completion_time": None,
            "error": None,
            "model_name": model_name,
            "model_version": SETTINGS.model_version,
        }
    )

    def client_fn(cid: str):
        return make_client_fn(model_name=model_name, num_clients=clients)(cid)

    try:
        FEDERATED_STATUS["status"] = "ROUND_RUNNING"
        history = start_simulation(
            client_fn=client_fn,
            num_clients=clients,
            config=ServerConfig(num_rounds=rounds),
            strategy=strategy,
        )

        final_parameters = strategy.last_aggregated_parameters
        if final_parameters is None:
            final_parameters = initial_parameters[0]

        checkpoint_path = _save_checkpoint(model_name, rounds, final_parameters)
        FEDERATED_STATUS["status"] = "COMPLETED"
        FEDERATED_STATUS["current_round"] = rounds
        FEDERATED_STATUS["completion_time"] = "simulated"
        FEDERATED_STATUS["participating_clients"] = clients

        model = adapter.create_model()
        adapter.set_parameters(model, final_parameters)
        city_metrics: dict[str, dict[str, float]] = {}
        all_X = []
        all_y = []
        for city_index in range(clients):
            city_id = f"city_{city_index}"
            X, y = adapter.load_city_dataset(city_id, num_clients=clients)
            city_metrics[city_id] = adapter.evaluate(model, X, y)
            all_X.append(X)
            all_y.append(y)

        global_metrics = adapter.evaluate(
            model,
            np.vstack(all_X),
            np.concatenate(all_y),
        )

        summary = {
            "status": "completed",
            "model_name": model_name,
            "model_version": SETTINGS.model_version,
            "rounds": rounds,
            "clients": clients,
            "checkpoint": str(checkpoint_path),
            "global_metrics": global_metrics,
            "city_metrics": city_metrics,
            "history": getattr(history, "losses_distributed", []),
        }
        FEDERATED_STATUS["metrics"] = summary["global_metrics"]
        return summary
    except Exception as exc:  # pragma: no cover - runtime guard
        logger.exception("Federated simulation failed.")
        FEDERATED_STATUS["status"] = "FAILED"
        FEDERATED_STATUS["error"] = str(exc)
        raise


if __name__ == "__main__":
    run_federated_simulation()


__all__ = ["FEDERATED_STATUS", "FederatedAveragingStrategy", "run_federated_simulation"]
