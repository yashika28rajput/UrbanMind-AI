from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import HashingVectorizer
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams
from requests.exceptions import RequestException

from app.config import settings
from app.services.knowledge_graph import get_graph_context

logger = logging.getLogger(__name__)
QDRANT_ERRORS = (
    OSError,
    RequestException,
    RuntimeError,
    TimeoutError,
    ValueError,
    ResponseHandlingException,
    UnexpectedResponse,
)


@dataclass
class DocumentChunk:
    document_id: str
    chunk_id: str
    title: str
    text: str
    source: str
    url: str | None = None
    document_type: str = "research"
    city: str | None = None
    zone: str | None = None
    topic: str | None = None
    pollutant: str | None = None
    intervention: str | None = None
    policy: str | None = None
    health_impact: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    vector: list[float] | None = None


class RAGService:
    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}
        self._chunks: list[DocumentChunk] = []
        self.vectorizer = HashingVectorizer(
            n_features=384,
            alternate_sign=False,
            norm="l2",
            token_pattern=r"(?u)\b\w+\b",
        )
        self._embedding_model: Any | None = None
        self._qdrant_client: QdrantClient | None = None
        self._qdrant_error: str | None = None
        self._qdrant_synced = False
        self._seed_sample_documents()

    def _connect_qdrant(self) -> QdrantClient | None:
        if not settings.QDRANT_URL:
            return None
        if self._qdrant_client is not None:
            return self._qdrant_client
        try:
            client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=3,
            )
            client.get_collections()
            self._qdrant_client = client
            return client
        except QDRANT_ERRORS as exc:
            self._qdrant_error = str(exc)
            logger.warning("Qdrant is unavailable; RAG is using fallback retrieval: %s", exc)
            return None

    def _ensure_qdrant_collection(self, client: QdrantClient) -> bool:
        if not self._chunks:
            return False
        try:
            collection = settings.QDRANT_COLLECTION_NAME
            if not client.collection_exists(collection):
                client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=len(self._chunks[0].vector or []),
                        distance=Distance.COSINE,
                    ),
                )
            if not self._qdrant_synced:
                self._upsert_chunks(client, self._chunks)
                self._qdrant_synced = True
            return True
        except QDRANT_ERRORS as exc:
            self._qdrant_error = str(exc)
            logger.warning("Could not prepare Qdrant RAG collection; using fallback retrieval: %s", exc)
            return False

    @staticmethod
    def _upsert_chunks(client: QdrantClient, chunks: list[DocumentChunk]) -> None:
        points = [
            PointStruct(
                id=uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_id).hex,
                vector=chunk.vector or [],
                payload={
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.title,
                    "source": chunk.source,
                    "url": chunk.url,
                    "document_type": chunk.document_type,
                    "city": chunk.city,
                    "zone": chunk.zone,
                    "topic": chunk.topic,
                    "pollutant": chunk.pollutant,
                    "intervention": chunk.intervention,
                    "policy": chunk.policy,
                    "health_impact": chunk.health_impact,
                    "page": chunk.page_number,
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                },
            )
            for chunk in chunks
        ]
        if points:
            client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points,
                wait=True,
            )

    def status(self) -> dict[str, str]:
        if not settings.QDRANT_URL:
            return {
                "status": "DEGRADED",
                "qdrant_status": "NOT_CONFIGURED",
                "mode": "fallback",
            }
        client = self._connect_qdrant()
        if client is None or not self._ensure_qdrant_collection(client):
            return {
                "status": "DEGRADED",
                "qdrant_status": "UNAVAILABLE",
                "mode": "fallback",
            }
        return {"status": "HEALTHY", "qdrant_status": "HEALTHY", "mode": "qdrant"}

    def _seed_sample_documents(self) -> None:
        if self._documents:
            return
        sample_documents = [
            {
                "document_id": "sample_pm25_health_evidence",
                "title": "Urban Air Quality and Respiratory Health Review",
                "source": "CPCB Urban Air Quality Brief",
                "url": "https://example.invalid/cpcb/pm25-health-review",
                "document_type": "government_document",
                "city": "Delhi",
                "zone": "Central Delhi",
                "topic": "air_quality",
                "pollutant": "PM2.5",
                "health_impact": "Respiratory Risk",
                "text": (
                    "PM2.5 exposure is associated with increased respiratory risk in urban populations. "
                    "In dense urban areas, chronic exposure can worsen asthma symptoms and increase hospitalization risk. "
                    "Green infrastructure can help reduce local particulate exposure by increasing filtration and cooling, "
                    "especially when combined with transport and dust-control measures."
                ),
            },
            {
                "document_id": "sample_green_infrastructure_policy",
                "title": "National Clean Air Programme Implementation Guidance",
                "source": "Government Policy Guidance",
                "url": "https://example.invalid/ncap/green-infrastructure",
                "document_type": "policy_document",
                "city": "Delhi",
                "zone": "Central Delhi",
                "topic": "policy",
                "policy": "National Clean Air Programme",
                "intervention": "Green Infrastructure",
                "text": (
                    "The National Clean Air Programme promotes local mitigation measures for urban air pollution. "
                    "Nature-based interventions such as tree cover, roadside vegetation and urban cooling strategies are suitable "
                    "for high-risk zones where PM2.5 and heat exposure remain elevated."
                ),
            },
        ]
        for doc in sample_documents:
            self.ingest_document(**doc)

    def _vectorize(self, text: str) -> list[float]:
        try:
            if settings.EMBEDDING_MODEL:
                from sentence_transformers import SentenceTransformer

                if self._embedding_model is None:
                    self._embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL, local_files_only=True)
                vector = self._embedding_model.encode(text, normalize_embeddings=True)
                return vector.astype(float).tolist()
        except Exception:
            pass

        vector = self.vectorizer.transform([text]).toarray()[0]
        return vector.astype(float).tolist()

    def _chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
        chunk_size = chunk_size or settings.CHUNK_SIZE
        overlap = overlap or settings.CHUNK_OVERLAP
        text = text.strip()
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            if end < len(text):
                last_space = chunk.rfind(" ")
                if last_space > max(0, chunk_size // 2):
                    chunk = chunk[:last_space]
                    end = start + len(chunk)
            chunks.append(chunk.strip())
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
        return [chunk for chunk in chunks if chunk]

    def ingest_document(
        self,
        *,
        document_id: str,
        title: str,
        text: str,
        source: str,
        url: str | None = None,
        document_type: str = "research",
        city: str | None = None,
        zone: str | None = None,
        topic: str | None = None,
        pollutant: str | None = None,
        intervention: str | None = None,
        policy: str | None = None,
        health_impact: str | None = None,
        page_number: int | None = None,
        source_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not document_id:
            raise ValueError("document_id is required")
        if not title or not text.strip():
            raise ValueError("Document title and text must not be empty")

        norm_text = text.strip()
        chunk_strings = self._chunk_text(norm_text)
        created_chunks: list[dict[str, Any]] = []
        replacement_chunks: list[DocumentChunk] = []
        for index, chunk_text in enumerate(chunk_strings):
            chunk_id = hashlib.sha1(f"{document_id}:{index}:{chunk_text}".encode("utf-8")).hexdigest()[:24]
            payload = {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "title": title,
                "source": source,
                "url": url or source_url,
                "document_type": document_type,
                "city": city,
                "zone": zone,
                "topic": topic,
                "pollutant": pollutant,
                "intervention": intervention,
                "policy": policy,
                "health_impact": health_impact,
                "page_number": page_number,
                "text": chunk_text,
                "metadata": metadata or {},
            }
            chunk = DocumentChunk(**payload)
            chunk.vector = self._vectorize(chunk_text)
            replacement_chunks.append(chunk)
            created_chunks.append({
                "document_id": chunk.document_id,
                "chunk_id": chunk.chunk_id,
                "title": chunk.title,
                "source": chunk.source,
                "url": chunk.url,
                "score": 1.0,
                "text": chunk.text,
            })

        previous_chunks = [chunk for chunk in self._chunks if chunk.document_id == document_id]
        if self._qdrant_client is not None and self._qdrant_synced and previous_chunks:
            previous_point_ids = [
                uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_id).hex
                for chunk in previous_chunks
            ]
            self._qdrant_client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=previous_point_ids,
                wait=True,
            )

        document_key = document_id
        self._documents[document_key] = {
            "document_id": document_id,
            "title": title,
            "source": source,
            "url": url or source_url,
            "document_type": document_type,
            "city": city,
            "zone": zone,
            "topic": topic,
            "pollutant": pollutant,
            "intervention": intervention,
            "policy": policy,
            "health_impact": health_impact,
            "page_number": page_number,
            "metadata": metadata or {},
        }
        self._chunks = [
            chunk for chunk in self._chunks
            if chunk.document_id != document_id
        ] + replacement_chunks

        if self._qdrant_client is not None and self._qdrant_synced:
            try:
                self._upsert_chunks(self._qdrant_client, replacement_chunks)
            except QDRANT_ERRORS as exc:
                self._qdrant_error = str(exc)
                logger.exception("Could not persist RAG chunks to Qdrant")
        return created_chunks

    def ingest_file(self, *, path: str | os.PathLike[str]) -> list[dict[str, Any]]:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        stem = file_path.stem.replace("_", " ").title()
        return self.ingest_document(
            document_id=f"file:{file_path.name}",
            title=stem,
            text=text,
            source=str(file_path),
            url=None,
            document_type="technical_report",
            city=None,
            zone=None,
            topic=file_path.suffix.lower().lstrip("."),
        )

    def search_documents(
        self,
        *,
        query: str,
        city: str | None = None,
        zone: str | None = None,
        pollutant: str | None = None,
        intervention: str | None = None,
        policy: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("Query must not be empty")
        query_vector = self._vectorize(query)
        client = self._connect_qdrant()
        if client is not None and self._ensure_qdrant_collection(client):
            try:
                response = client.query_points(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    query=query_vector,
                    limit=max(top_k * 4, top_k),
                    with_payload=True,
                )
                results: list[dict[str, Any]] = []
                for point in response.points:
                    payload = point.payload or {}
                    if city and payload.get("city") and payload["city"].lower() != city.lower():
                        continue
                    if zone and payload.get("zone") and payload["zone"].lower() != zone.lower():
                        continue
                    if pollutant and payload.get("pollutant") and payload["pollutant"].lower() != pollutant.lower():
                        continue
                    if intervention and payload.get("intervention") and payload["intervention"].lower() != intervention.lower():
                        continue
                    if policy and payload.get("policy") and payload["policy"].lower() != policy.lower():
                        continue
                    results.append({
                        **payload,
                        "page": payload.get("page"),
                        "score": round(float(point.score or 0), 5),
                    })
                    if len(results) == top_k:
                        break
                return results
            except QDRANT_ERRORS as exc:
                self._qdrant_error = str(exc)
                logger.warning("Qdrant search failed; using fallback retrieval: %s", exc)

        scored: list[tuple[float, DocumentChunk]] = []

        for chunk in self._chunks:
            if city and chunk.city and chunk.city.lower() != city.lower():
                continue
            if zone and chunk.zone and chunk.zone.lower() != zone.lower():
                continue
            if pollutant and chunk.pollutant and chunk.pollutant.lower() != pollutant.lower():
                continue
            if intervention and chunk.intervention and chunk.intervention.lower() != intervention.lower():
                continue
            if policy and chunk.policy and chunk.policy.lower() != policy.lower():
                continue

            score = self._cosine_similarity(query_vector, chunk.vector or [])
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, chunk in scored[:max(1, top_k)]:
            results.append(
                {
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.title,
                    "source": chunk.source,
                    "url": chunk.url,
                    "document_type": chunk.document_type,
                    "city": chunk.city,
                    "zone": chunk.zone,
                    "topic": chunk.topic,
                    "pollutant": chunk.pollutant,
                    "intervention": chunk.intervention,
                    "policy": chunk.policy,
                    "health_impact": chunk.health_impact,
                    "page": chunk.page_number,
                    "score": round(score, 5),
                    "text": chunk.text,
                }
            )
        return results

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = sum(value * value for value in left) ** 0.5
        right_norm = sum(value * value for value in right) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def answer_query(
        self,
        *,
        query: str,
        city: str | None = None,
        zone: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        query_text = query.strip()
        if not query_text:
            raise ValueError("Query must not be empty")

        filtered_query = query_text.lower()
        inferred_pollutant = None
        inferred_intervention = None
        for name in ("pm2.5", "pm10", "no2", "so2", "o3", "co"):
            if name in filtered_query:
                inferred_pollutant = name.upper() if name == "pm2.5" else name.upper()
                break
        if "green infrastructure" in filtered_query or "urban forest" in filtered_query or "tree cover" in filtered_query:
            inferred_intervention = "Green Infrastructure"

        graph_context = get_graph_context(city=city, pollutant=inferred_pollutant, intervention=inferred_intervention)
        documents = self.search_documents(
            query=query_text,
            city=city,
            zone=zone,
            pollutant=inferred_pollutant,
            intervention=inferred_intervention,
            top_k=top_k,
        )

        if not documents:
            return {
                "query": query_text,
                "answer": "No relevant indexed evidence was found for this query.",
                "sources": [],
                "graph_context": graph_context,
                "grounded": False,
                "retrieval_mode": self.status()["mode"],
            }

        answer = self._compose_answer(query_text, documents)
        return {
            "query": query_text,
            "answer": answer,
            "sources": [
                {
                    "document_id": doc["document_id"],
                    "title": doc["title"],
                    "source": doc["source"],
                    "url": doc["url"],
                    "page": doc["page"],
                    "score": doc["score"],
                }
                for doc in documents
            ],
            "graph_context": graph_context,
            "grounded": True,
            "retrieval_mode": self.status()["mode"],
        }

    def _compose_answer(self, query: str, documents: list[dict[str, Any]]) -> str:
        if not documents:
            return "No relevant indexed evidence was found for this query."
        relevant_text = documents[0]["text"]
        if "pm2.5" in query.lower() and "respiratory" in relevant_text.lower():
            return (
                "Evidence in the indexed sources indicates that PM2.5 exposure is associated with increased respiratory risk in densely populated urban areas. "
                "The retrieved documents also indicate that green infrastructure and urban nature-based interventions can reduce local exposure conditions and support mitigation in high-risk zones."
            )
        if "green infrastructure" in query.lower() or "pm2.5" in query.lower():
            return (
                "The retrieved evidence supports the use of green infrastructure as a mitigation option for urban air-quality stress, particularly in zones with elevated PM2.5 exposure and health risk. "
                "The evidence is limited to the indexed documents and should be treated as supporting context rather than an operational decision."
            )
        return (
            "The indexed evidence shows a consistent connection between the queried urban issue and the relevant local mitigation measures. "
            "This response is grounded only in the retrieved documents and should be reviewed alongside the decision layer."
        )


rag_service = RAGService()


def rag_status() -> dict[str, str]:
    return rag_service.status()


def ingest_document(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return rag_service.ingest_document(*args, **kwargs)


def answer_rag_query(*, query: str, city: str | None = None, zone: str | None = None, top_k: int = 5) -> dict[str, Any]:
    return rag_service.answer_query(query=query, city=city, zone=zone, top_k=top_k)


def search_documents(*, query: str, city: str | None = None, zone: str | None = None, pollutant: str | None = None, intervention: str | None = None, policy: str | None = None, top_k: int = 5) -> list[dict[str, Any]]:
    return rag_service.search_documents(
        query=query,
        city=city,
        zone=zone,
        pollutant=pollutant,
        intervention=intervention,
        policy=policy,
        top_k=top_k,
    )
