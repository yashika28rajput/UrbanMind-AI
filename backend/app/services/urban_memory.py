import os
from datetime import datetime
from typing import Any
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from sklearn.feature_extraction.text import HashingVectorizer

from app.database.urban_memory_store import (
    UrbanMemory,
    count_memories,
    fetch_memories,
    fetch_memory,
    get_database_backend,
    insert_memory,
    update_memory_outcome as persist_memory_outcome,
)

MEMORY_TYPES = {
    "policy",
    "simulation",
    "environment",
    "recommendation",
    "intervention",
    "decision_log",
}
OUTCOMES = {"success", "failure", "ongoing", "unknown"}
VECTOR_DIMENSION = 384
_vectorizer = HashingVectorizer(
    n_features=VECTOR_DIMENSION,
    alternate_sign=False,
    norm="l2",
    token_pattern=r"(?u)\b\w+\b",
)
_sentence_model: Any | None = None
_sentence_model_name: str | None = None
_qdrant_client: QdrantClient | None = None
_qdrant_vector_size: int | None = None


def _embedding(text: str) -> tuple[list[float], str]:
    global _sentence_model, _sentence_model_name, _qdrant_vector_size
    model_name = os.getenv("URBAN_MEMORY_EMBEDDING_MODEL")
    if model_name:
        if _sentence_model is None:
            from sentence_transformers import SentenceTransformer

            _sentence_model = SentenceTransformer(model_name, local_files_only=True)
            _sentence_model_name = model_name
        vector = _sentence_model.encode(text, normalize_embeddings=True)
        result = vector.tolist()
        _qdrant_vector_size = len(result)
        return result, f"sentence-transformers:{_sentence_model_name}"

    vector = _vectorizer.transform([text]).toarray()[0]
    result = vector.tolist()
    _qdrant_vector_size = len(result)
    return result, f"sklearn-hashing:{VECTOR_DIMENSION}"


def _get_qdrant_client() -> QdrantClient | None:
    global _qdrant_client
    url = os.getenv("QDRANT_URL")
    if not url:
        return None
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=url, api_key=os.getenv("QDRANT_API_KEY"))
    return _qdrant_client


def _ensure_qdrant_collection() -> QdrantClient | None:
    client = _get_qdrant_client()
    if client is None:
        return None
    if _qdrant_vector_size is None:
        raise RuntimeError("Create or search a memory embedding before initializing Qdrant.")
    collection_name = os.getenv("QDRANT_COLLECTION", "urban_memories")
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=_qdrant_vector_size, distance=Distance.COSINE),
        )
    return client


def _index_in_qdrant(memory: UrbanMemory) -> None:
    client = _ensure_qdrant_collection()
    if client is None:
        return
    collection_name = os.getenv("QDRANT_COLLECTION", "urban_memories")
    client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=memory.id,
                vector=memory.embedding,
                payload={
                    "memory_id": memory.id,
                    "memory_type": memory.memory_type,
                    "city": memory.city,
                    "zone": memory.zone,
                    "outcome": memory.outcome,
                },
            )
        ],
        wait=True,
    )


def _memory_text(title: str, content: str, structured_data: dict[str, Any]) -> str:
    structured_text = " ".join(
        f"{key} {value}"
        for key, value in structured_data.items()
        if value is not None and not isinstance(value, (dict, list))
    )
    return f"{title}\n{content}\n{structured_text}".strip()


def _serialize(memory: UrbanMemory, score: float | None = None) -> dict[str, Any]:
    result = {
        "id": memory.id,
        "type": memory.memory_type,
        "city": memory.city,
        "zone": memory.zone,
        "title": memory.title,
        "content": memory.content,
        "structured_data": memory.structured_data,
        "outcome": memory.outcome,
        "source_ref": memory.source_ref,
        "embedding_provider": memory.embedding_provider,
        "created_at": memory.created_at.isoformat() if isinstance(memory.created_at, datetime) else memory.created_at,
    }
    if score is not None:
        result["similarity"] = round(score, 5)
    return result


def _validate_and_prepare(
    *,
    memory_type: str,
    city: str,
    zone: str | None,
    title: str,
    content: str,
    structured_data: dict[str, Any],
    outcome: str | None,
    source_ref: str | None,
    memory_id: str | None = None,
) -> dict[str, Any]:
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"Unsupported memory type: {memory_type}")
    if outcome is not None and outcome not in OUTCOMES:
        raise ValueError(f"Unsupported outcome: {outcome}")
    if not city.strip() or not title.strip() or not content.strip():
        raise ValueError("City, title, and content must not be empty.")
    text = _memory_text(title, content, structured_data)
    embedding, provider = _embedding(text)
    return {
        "id": memory_id or str(uuid4()),
        "memory_type": memory_type,
        "city": city.strip(),
        "zone": zone.strip() if zone and zone.strip() else None,
        "title": title.strip(),
        "content": content.strip(),
        "structured_data": structured_data,
        "outcome": outcome,
        "source_ref": source_ref.strip() if source_ref and source_ref.strip() else None,
        "embedding": embedding,
        "embedding_provider": provider,
    }


def create_memory(
    *,
    memory_type: str,
    city: str,
    zone: str | None,
    title: str,
    content: str,
    structured_data: dict[str, Any],
    outcome: str | None,
    source_ref: str | None = None,
) -> dict[str, Any]:
    values = _validate_and_prepare(
        memory_type=memory_type,
        city=city,
        zone=zone,
        title=title,
        content=content,
        structured_data=structured_data,
        outcome=outcome,
        source_ref=source_ref,
    )
    memory, created = insert_memory(values)
    _index_in_qdrant(memory)
    result = _serialize(memory)
    result["created"] = created
    return result


def get_memory(memory_id: str) -> dict[str, Any] | None:
    memory = fetch_memory(memory_id)
    return _serialize(memory) if memory else None


def update_memory_outcome(
    memory_id: str,
    *,
    outcome: str,
    outcome_notes: str | None = None,
) -> dict[str, Any] | None:
    if outcome not in OUTCOMES:
        raise ValueError(f"Unsupported outcome: {outcome}")
    memory = fetch_memory(memory_id)
    if memory is None:
        return None

    content = memory.content
    structured_data = dict(memory.structured_data)
    if outcome_notes and outcome_notes.strip():
        note = outcome_notes.strip()
        content = f"{content}\nObserved outcome: {note}"
        notes = structured_data.get("outcome_notes", [])
        if not isinstance(notes, list):
            notes = [str(notes)]
        structured_data["outcome_notes"] = [*notes, note]

    embedding, provider = _embedding(_memory_text(memory.title, content, structured_data))
    updated = persist_memory_outcome(
        memory_id,
        outcome=outcome,
        content=content,
        structured_data=structured_data,
        embedding=embedding,
        embedding_provider=provider,
    )
    if updated is None:
        return None
    _index_in_qdrant(updated)
    return _serialize(updated)


def list_memories(
    *,
    memory_type: str | None = None,
    city: str | None = None,
    zone: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return [
        _serialize(memory)
        for memory in fetch_memories(
            memory_type=memory_type,
            city=city,
            zone=zone,
            limit=limit,
            offset=offset,
        )
    ]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError(
            "Memory embeddings have inconsistent dimensions. Keep one embedding model "
            "configured or re-import memories after changing it."
        )
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def search_memories(
    query: str,
    *,
    memory_type: str | None = None,
    city: str | None = None,
    zone: str | None = None,
    outcome: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    query_text = query.strip()
    if len(query_text) < 2:
        raise ValueError("Search query must contain at least two characters.")
    if memory_type is not None and memory_type not in MEMORY_TYPES:
        raise ValueError(f"Unsupported memory type: {memory_type}")
    if outcome is not None and outcome not in OUTCOMES:
        raise ValueError(f"Unsupported outcome: {outcome}")

    query_vector, _ = _embedding(query_text)
    client = _ensure_qdrant_collection()
    if client is not None:
        conditions = []
        for key, value in (
            ("memory_type", memory_type),
            ("city", city),
            ("zone", zone),
            ("outcome", outcome),
        ):
            if value is not None:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        response = client.query_points(
            collection_name=os.getenv("QDRANT_COLLECTION", "urban_memories"),
            query=query_vector,
            query_filter=Filter(must=conditions) if conditions else None,
            limit=limit,
            with_payload=True,
        )
        results = []
        for point in response.points:
            memory_id = (point.payload or {}).get("memory_id")
            memory = fetch_memory(str(memory_id)) if memory_id else None
            if memory is not None:
                results.append(_serialize(memory, float(point.score)))
        return results

    candidates = fetch_memories(
        memory_type=memory_type,
        city=city,
        zone=zone,
        limit=max(count_memories(), 1),
        offset=0,
    )
    scored = [
        (_cosine_similarity(query_vector, memory.embedding), memory)
        for memory in candidates
        if outcome is None or memory.outcome == outcome
    ]
    scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    return [_serialize(memory, score) for score, memory in scored[:limit] if score > 0]


def get_memory_status() -> dict[str, Any]:
    embedding, _ = _embedding("UrbanMind memory status")
    client = _ensure_qdrant_collection()
    qdrant_configured = client is not None
    return {
        "status": "ready",
        "database_backend": get_database_backend(),
        "vector_backend": "qdrant" if qdrant_configured else "relational-embedding-index",
        "embedding_provider": (
            f"sentence-transformers:{os.getenv('URBAN_MEMORY_EMBEDDING_MODEL')}"
            if os.getenv("URBAN_MEMORY_EMBEDDING_MODEL")
            else f"sklearn-hashing:{VECTOR_DIMENSION}"
        ),
        "embedding_dimensions": len(embedding),
        "memory_count": count_memories(),
        "qdrant_configured": qdrant_configured,
        "sentence_transformer_model_configured": bool(os.getenv("URBAN_MEMORY_EMBEDDING_MODEL")),
    }
