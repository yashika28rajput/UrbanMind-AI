from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class LocalCityDataset:
    city_id: str
    data_path: str | Path
    target_column: str = "AQI"

    def load(self) -> pd.DataFrame:
        frame = pd.read_csv(self.data_path)
        if self.target_column not in frame.columns:
            raise ValueError(f"Target column '{self.target_column}' is missing from local city data: {self.data_path}")
        return frame

    def preprocess(self) -> tuple[np.ndarray, np.ndarray]:
        frame = self.load()
        excluded = {"AQI", "AQI_category", "location_id", "station_name", "timestamp_local"}
        feature_columns = [column for column in frame.columns if column not in excluded]
        X = frame[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)
        y = frame[self.target_column].astype(float).to_numpy()
        return X.to_numpy(dtype=float), y


__all__ = ["LocalCityDataset"]
