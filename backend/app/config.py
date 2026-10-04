from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_NAME: str = "urbanmind_knowledge"

    AUTH_REQUIRED: bool = False
    AUTH_USERNAME: str | None = None
    AUTH_PASSWORD_HASH: str | None = None
    AUTH_SECRET_KEY: str | None = None

    EMBEDDING_MODEL: str | None = None
    LLM_MODEL: str | None = None
    LLM_API_KEY: str | None = None

    NEO4J_URI: str | None = None
    NEO4J_USERNAME: str | None = None
    NEO4J_PASSWORD: str | None = None
    USE_NEO4J: bool = False

    TOP_K: int = 5
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 60
    USE_RERANKER: bool = False


settings = Settings()
