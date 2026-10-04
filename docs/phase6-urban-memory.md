# Phase 6 — Urban Memory Engine

The Urban Memory Engine stores past policies, recommendations, environmental
conditions, intervention simulations, observed intervention outcomes, and
decision logs. Memories are scoped by city and optional ward/zone and retain
structured source data alongside searchable text.

## Run it

Start the FastAPI application from the `backend` directory as usual. The API
creates its tables on first use.

By default, development uses a persistent SQLite database at
`backend/app/database/urban_memory.sqlite3`. Set `DATABASE_URL` in
`backend/.env` to use PostgreSQL instead, for example:

```text
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/urbanmind
```

If `QDRANT_URL` is configured, vectors are indexed in the configured Qdrant
collection (`QDRANT_COLLECTION`, default `urban_memories`). Without a Qdrant
service, vectors remain in the primary database and semantic similarity search
continues to work there. An optional `QDRANT_API_KEY` is used for authenticated
Qdrant services.

The default is a local 384-dimensional scikit-learn feature-hashing vector.
It provides lightweight lexical vector similarity, not language-model semantic
understanding, and does not download a model. For semantic embeddings, set
`URBAN_MEMORY_EMBEDDING_MODEL` to a locally cached Sentence Transformers model
name or path. The configured model must already be available locally; loading
is configured not to download files. Keep the embedding model unchanged after
ingesting memories unless you plan to re-import/re-embed existing records.

To load the Phase 2–5 CSV outputs into memory, run this from the `backend`
directory:

```text
python -m app.services.import_urban_memory
```

The import is idempotent. Existing environmental and decision/scenario rows
are recorded as historical context; simulations and recommendations are marked
with an unknown outcome unless the source contains an observed success/failure
status. Projected scenario impact is not represented as a measured real-world
result.

## API

- `GET /api/v1/memory/status` reports storage, embedding, vector backend, and
  record count.
- `POST /api/v1/memory/memories` stores a policy, simulation, environmental
  snapshot, recommendation, intervention result, or decision log.
- `GET /api/v1/memory/memories` lists memories with type/city/zone filters and
  pagination.
- `GET /api/v1/memory/memories/{id}` retrieves one memory.
- `PATCH /api/v1/memory/memories/{id}/outcome` records a later observed result
  and notes, updating the searchable embedding as well.
- `POST /api/v1/memory/search` performs vector similarity search with optional
  type/city/zone/outcome filters.

Search scores rank historical context; they do not establish causality or
replace the decision and prediction layers.
