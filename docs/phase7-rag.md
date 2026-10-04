# Phase 7 — Knowledge Graph + RAG

This project now includes a modular knowledge/evidence layer for UrbanMind AI.

## Components

- Knowledge graph with a seeded Delhi/PM2.5/health/risk example
- Optional Neo4j-ready abstraction with in-memory fallback
- Chunked document ingestion for text-based sources
- Lightweight vector retrieval with optional Sentence Transformers
- Grounded query endpoint that returns citations and graph context

## API examples

POST /api/v1/rag/query

```json
{
  "query": "How can green infrastructure reduce PM2.5 risk in Delhi?",
  "city": "Delhi",
  "top_k": 5
}
```

POST /api/v1/knowledge-graph/query

```json
{
  "entity": "PM2.5",
  "entity_type": "Pollutant"
}
```

## Local ingestion

```bash
cd backend
python -m app.scripts.ingest_documents --path ../data
```
