# Phase 15 — Decision Intelligence Dashboard

The React + TypeScript dashboard lives in `frontend/` and uses the existing
FastAPI services. From the repository root:

```powershell
cd frontend
npm install
npm run test
npm run dev
```

Run the backend separately from `backend/` using the existing environment and
ASGI application (`uvicorn app.main:app --reload`). The Vite development server
proxies `/api` and `/health` to `http://127.0.0.1:8000`. Set
`VITE_API_BASE_URL` to the API prefix (for example, `https://api.example/api/v1`)
when the dashboard is hosted separately.

## Dashboard authentication

Authentication is opt-in to preserve existing API clients and local Phase 1–14
workflows. To require authentication for `/api/v1` routes, configure
`AUTH_REQUIRED=true`, `AUTH_USERNAME`, `AUTH_PASSWORD_HASH`, and
`AUTH_SECRET_KEY` in the backend environment file. Do not commit this file.

Generate a password hash and signing secret without placing a password in
source code:

```powershell
python -c "from getpass import getpass; from app.services.dashboard_auth import hash_password; print(hash_password(getpass()))"
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The password hash uses PBKDF2-HMAC-SHA256. Access tokens are signed HS256 JWTs
with an eight-hour lifetime; the dashboard stores them in tab-scoped
`sessionStorage`. The login and auth-configuration endpoints remain public.
When authentication is required but incompletely configured, the API returns a
service error instead of allowing access.

## Data and availability

The map endpoint serves the existing Delhi ward polygons with Digital Twin
metrics attached. Dashboard metrics, generated scenarios, simulations,
optimization, explanations, and evidence are read from backend APIs. Missing
numerical results are shown as unavailable. System status reports current
database, model-metadata, Digital Twin, RAG, and Qdrant checks.

Set `QDRANT_URL` (and `QDRANT_API_KEY` where required) to enable persistent RAG
vectors. The existing in-process retrieval remains available when Qdrant is
not configured or is unreachable, and the API identifies that mode as
degraded/fallback rather than reporting persistent storage as healthy.
