import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FederatedSettings:
    model_name: str = os.getenv("FEDERATED_MODEL_NAME", "aqi_model")
    model_version: str = os.getenv("FEDERATED_MODEL_VERSION", "1.0")
    server_address: str = os.getenv("FEDERATED_SERVER_ADDRESS", "0.0.0.0:9090")
    num_rounds: int = int(os.getenv("FEDERATED_NUM_ROUNDS", "3"))
    local_epochs: int = int(os.getenv("FEDERATED_LOCAL_EPOCHS", "1"))
    batch_size: int = int(os.getenv("FEDERATED_BATCH_SIZE", "32"))
    learning_rate: float = float(os.getenv("FEDERATED_LEARNING_RATE", "0.001"))
    max_clients: int = int(os.getenv("FEDERATED_MAX_CLIENTS", "5"))


SETTINGS = FederatedSettings()
