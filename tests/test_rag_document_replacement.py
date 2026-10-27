from __future__ import annotations

import uuid

from app.config import settings
from app.services.rag_service import RAGService


def _ingest(service: RAGService, text: str) -> None:
    service.ingest_document(
        document_id="refresh-target",
        title="Refresh target",
        text=text,
        source="test fixture",
    )


def test_reingesting_document_replaces_old_fallback_chunks(monkeypatch) -> None:
    monkeypatch.setattr(settings, "QDRANT_URL", None)
    service = RAGService()

    _ingest(service, "obsoleteambermarker archived evidence")
    _ingest(service, "currentblueevidence replacement text")

    stale_results = service.search_documents(query="obsoleteambermarker", top_k=5)
    current_results = service.search_documents(query="currentblueevidence", top_k=5)

    assert not any(result["document_id"] == "refresh-target" for result in stale_results)
    assert any(result["document_id"] == "refresh-target" for result in current_results)
    assert len([chunk for chunk in service._chunks if chunk.document_id == "refresh-target"]) == 1


def test_reingesting_document_deletes_old_qdrant_points_before_upserting_new_ones(monkeypatch) -> None:
    class FakeQdrantClient:
        def __init__(self) -> None:
            self.deleted: list[str] = []
            self.upserted: list[str] = []

        def delete(self, *, collection_name: str, points_selector: list[str], wait: bool) -> None:
            assert collection_name == settings.QDRANT_COLLECTION_NAME
            assert wait is True
            self.deleted.extend(points_selector)

        def upsert(self, *, collection_name: str, points: list[object], wait: bool) -> None:
            assert collection_name == settings.QDRANT_COLLECTION_NAME
            assert wait is True
            self.upserted.extend(str(point.id) for point in points)

    monkeypatch.setattr(settings, "QDRANT_URL", None)
    service = RAGService()
    _ingest(service, "obsoleteambermarker archived evidence")
    previous_chunk = next(chunk for chunk in service._chunks if chunk.document_id == "refresh-target")
    client = FakeQdrantClient()
    service._qdrant_client = client  # type: ignore[assignment]
    service._qdrant_synced = True

    _ingest(service, "currentblueevidence replacement text")

    replacement_chunk = next(chunk for chunk in service._chunks if chunk.document_id == "refresh-target")
    previous_point_id = uuid.uuid5(uuid.NAMESPACE_URL, previous_chunk.chunk_id).hex
    replacement_point_id = uuid.uuid5(uuid.NAMESPACE_URL, replacement_chunk.chunk_id).hex
    assert client.deleted == [previous_point_id]
    assert client.upserted == [replacement_point_id]
