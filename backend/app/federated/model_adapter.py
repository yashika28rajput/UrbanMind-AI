from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


class AQIModelAdapter:
    """Small, reproducible AQI model adapter for federated learning."""

    TARGET_COLUMN = "AQI"
    EXCLUDED_COLUMNS = {"AQI", "AQI_category", "location_id", "station_name", "timestamp_local"}

    def __init__(self, model_name: str = "aqi_model") -> None:
        self.model_name = model_name
        self.root_dir = Path(__file__).resolve().parents[3]
        self.data_path = self.root_dir / "data" / "processed" / "ml" / "aqi" / "delhi_aqi_train.csv"
        self.feature_columns = self._load_feature_columns()

    def _load_feature_columns(self) -> list[str]:
        df = pd.read_csv(self.data_path)
        feature_columns = [
            column
            for column in df.columns
            if column not in self.EXCLUDED_COLUMNS
        ]
        if not feature_columns:
            raise ValueError("No AQI feature columns were found in the training dataset.")
        return feature_columns

    def create_model(self) -> LinearRegression:
        model = LinearRegression()
        model.n_features_in_ = len(self.feature_columns)
        model.coef_ = np.zeros(len(self.feature_columns), dtype=float)
        model.intercept_ = 0.0
        return model

    def get_parameters(self, model: LinearRegression) -> np.ndarray:
        coef = np.asarray(model.coef_, dtype=float).reshape(-1)
        intercept = np.asarray([float(model.intercept_)], dtype=float)
        return np.concatenate([coef, intercept])

    def set_parameters(self, model: LinearRegression, parameters: np.ndarray | list[float]) -> LinearRegression:
        values = np.asarray(parameters, dtype=float).reshape(-1)
        if values.size < 2:
            raise ValueError("Model parameters must include both coefficients and the intercept.")
        coef = values[:-1]
        intercept = float(values[-1])
        model.n_features_in_ = len(self.feature_columns)
        model.coef_ = coef.astype(float)
        model.intercept_ = intercept
        return model

    def load_city_dataset(self, city_id: str, *, num_clients: int = 3) -> tuple[np.ndarray, np.ndarray]:
        df = pd.read_csv(self.data_path)
        city_partition = self._partition_for_city(df, city_id, num_clients=num_clients)
        X = city_partition[self.feature_columns].copy()
        y = city_partition[self.TARGET_COLUMN].astype(float).to_numpy()
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.astype(float)
        if X.isna().any().any():
            X = X.fillna(0.0)
        return X.to_numpy(dtype=float), y.astype(float)

    def _partition_for_city(self, df: pd.DataFrame, city_id: str, *, num_clients: int) -> pd.DataFrame:
        if num_clients < 1:
            raise ValueError("At least one client is required for simulation.")
        client_order = [f"city_{index}" for index in range(num_clients)]
        if city_id not in client_order:
            city_index = abs(hash(city_id)) % num_clients
        else:
            city_index = client_order.index(city_id)

        indices = np.array_split(np.arange(len(df)), num_clients)
        return df.iloc[indices[city_index]].copy()

    def evaluate(self, model: LinearRegression, X: np.ndarray, y: np.ndarray) -> dict[str, float]:
        predictions = model.predict(X)
        mae = mean_absolute_error(y, predictions)
        rmse = float(np.sqrt(mean_squared_error(y, predictions)))
        r2 = r2_score(y, predictions)
        return {"mae": float(mae), "rmse": rmse, "r2": float(r2)}

    def save_metadata(self, metrics: dict[str, float]) -> dict[str, object]:
        metadata = {
            "model_name": self.model_name,
            "model_version": "1.0",
            "target": self.TARGET_COLUMN,
            "features": self.feature_columns,
            "metrics": metrics,
        }
        path = self.root_dir / "models" / "federated" / "aqi" / "aqi_model_metadata.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata


__all__ = ["AQIModelAdapter"]
