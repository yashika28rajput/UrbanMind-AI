# Phase 8 — Federated Learning

UrbanMind AI uses federated learning to improve shared city intelligence without centralizing raw local data. Each city trains locally on its own dataset, sends only model updates and metrics to a shared server, and receives a globally aggregated model in return.

## Architecture

```text
Federated Server
  |
  v
Global Model
  |
  +--> City A local training --> model update
  +--> City B local training --> model update
  +--> City C local training --> model update
```

The server never loads raw city datasets. The protocol is intentionally limited to model parameters, metadata, and aggregated metrics.

## Why this matters

Urban planning data is non-IID across cities: Delhi, Noida, and other regions vary in pollution, weather, land cover, and traffic patterns. Federated learning enables collaborative improvement while keeping those local datasets inside their own environments.

## Privacy and limitations

This phase implements local data isolation and FedAvg aggregation. It does not claim absolute privacy. In future work the project can add secure aggregation, differential privacy, gradient clipping, encryption, and trusted execution environments.

## Flower integration

The current implementation uses Flower's simulation API to run a small multi-city AQI experiment in-process. The client model is an AQI adapter using a LinearRegression model trained on the same AQI feature set already present in the repository.

## Configuration

Environment variables can be set in `backend/.env` or by exporting values before startup:

```bash
FEDERATED_MODEL_NAME=aqi_model
FEDERATED_MODEL_VERSION=1.0
FEDERATED_NUM_ROUNDS=3
FEDERATED_LOCAL_EPOCHS=1
FEDERATED_BATCH_SIZE=32
FEDERATED_LEARNING_RATE=0.001
```

## Running the simulation

```bash
cd backend
python -m app.federated.server
```

The simulation will start a Flower training run across a small number of auto-generated city partitions and save checkpoints under `models/federated/aqi/`.

## API controls

FastAPI endpoints are exposed under `/api/v1/federated/*`:

- `POST /api/v1/federated/start`
- `GET /api/v1/federated/status`
- `GET /api/v1/federated/metrics`
- `GET /api/v1/federated/model`

## Adding a new city

To add a new city, configure a separate city partition and connect a new client instance to the same training flow. The server logic remains unchanged.

## Adding a new model

Implement a new model adapter using the same `get_parameters`/`set_parameters`/`evaluate` pattern and register it in the model registry or the simulation config.

## Evaluation

The framework reports per-city metrics after each simulation and records round-level metadata. No raw city data is exposed through the API or experiment logging.
