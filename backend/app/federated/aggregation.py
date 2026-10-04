from __future__ import annotations

import numpy as np


def weighted_average(parameter_arrays: list[np.ndarray], sample_counts: list[int]) -> np.ndarray:
    if not parameter_arrays:
        raise ValueError("No client parameters were provided for aggregation.")
    if len(parameter_arrays) != len(sample_counts):
        raise ValueError("Parameter arrays and sample counts must have the same length.")

    total_samples = sum(sample_counts)
    if total_samples <= 0:
        raise ValueError("Total sample count for aggregation must be positive.")

    aggregated = np.zeros_like(parameter_arrays[0], dtype=float)
    for params, count in zip(parameter_arrays, sample_counts):
        if params.shape != aggregated.shape:
            raise ValueError(
                "Client parameter shapes do not match during federated aggregation: "
                f"expected {aggregated.shape}, received {params.shape}."
            )
        aggregated += (count / total_samples) * np.asarray(params, dtype=float)

    return aggregated


def fedavg_aggregate(parameter_arrays: list[np.ndarray], sample_counts: list[int]) -> np.ndarray:
    return weighted_average(parameter_arrays, sample_counts)


__all__ = ["fedavg_aggregate", "weighted_average"]
