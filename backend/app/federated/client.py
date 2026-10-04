from __future__ import annotations

from typing import Any

import numpy as np
from flwr.client import NumPyClient
from sklearn.model_selection import train_test_split

from .config import SETTINGS
from .model_adapter import AQIModelAdapter


class AQIClient(NumPyClient):
    def __init__(self, city_id: str, *, num_clients: int = 3, model_name: str = "aqi_model") -> None:
        self.city_id = city_id
        self.adapter = AQIModelAdapter(model_name=model_name)
        self.model = self.adapter.create_model()
        train_X, train_y = self.adapter.load_city_dataset(city_id, num_clients=num_clients)
        self.train_X, self.test_X, self.train_y, self.test_y = train_test_split(
            train_X,
            train_y,
            test_size=0.2,
            random_state=42,
            shuffle=True,
        )

    def get_parameters(self, config: dict[str, Any]) -> list[np.ndarray]:
        return [self.adapter.get_parameters(self.model)]

    def set_parameters(self, parameters: list[np.ndarray]) -> None:
        if not parameters:
            return
        self.model = self.adapter.set_parameters(self.model, parameters[0])

    def fit(self, parameters: list[np.ndarray], config: dict[str, Any]) -> tuple[list[np.ndarray], int, dict[str, Any]]:
        self.set_parameters(parameters)
        epochs = int(config.get("local_epochs", SETTINGS.local_epochs))
        for _ in range(epochs):
            self.model.fit(self.train_X, self.train_y)
        metrics = {
            "city_id": self.city_id,
            "samples": int(len(self.train_X)),
            "local_epochs": epochs,
            "loss": float(np.mean((self.model.predict(self.train_X) - self.train_y) ** 2)),
        }
        return [self.adapter.get_parameters(self.model)], len(self.train_X), metrics

    def evaluate(self, parameters: list[np.ndarray], config: dict[str, Any]) -> tuple[float, int, dict[str, Any]]:
        self.set_parameters(parameters)
        metrics = self.adapter.evaluate(self.model, self.test_X, self.test_y)
        loss = float(metrics["rmse"])
        return loss, len(self.test_X), {"city_id": self.city_id, **metrics}


def make_client_fn(*, model_name: str = "aqi_model", num_clients: int = 3):
    city_ids = [f"city_{index}" for index in range(num_clients)]

    def client_fn(cid: str):
        index = int(cid)
        city_id = city_ids[index % len(city_ids)]
        return AQIClient(city_id, num_clients=num_clients, model_name=model_name).to_client()

    return client_fn


__all__ = ["AQIClient", "make_client_fn"]
