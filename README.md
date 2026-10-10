# UrbanMind AI

UrbanMind AI is a decision intelligence platform for sustainable urban planning.

## Current status

- Phase 4: prediction layer
- Phase 5: digital twin
- Phase 6: urban memory engine
- Phase 7: knowledge graph + RAG layer
- Phase 8: privacy-preserving federated learning layer
- Phase 9: multi-agent AI workflow layer
- Phase 10: evidence-aware urban intervention scenario generation
- Phase 11: Digital Twin scenario simulation
- Phase 12: constraint-aware Pareto optimization
- Phase 13: SHAP explainability and counterfactual analysis
- Phase 15: Urban Decision Intelligence Dashboard

See docs/phase7-rag.md for the Phase 7 API and usage notes.
See docs/phase10-scenarios.md for the Phase 10 scenario API and validation behavior.
See docs/phases11-13.md for simulation, optimization, explainability, and the
complete scenario-to-report pipeline.
See docs/phase15-dashboard.md for dashboard setup, authentication, and service
configuration.


## Running locally (Windows PowerShell)

Run from the repository root (the folder that contains `backend/`, `frontend/` and `tests/`).

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env   # then edit; never commit .env
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

```powershell
# Frontend (new terminal, from repository root)
cd frontend
npm ci
npm run dev        # http://localhost:5173, proxies /api to http://127.0.0.1:8000
```

Check it is running: `Invoke-RestMethod http://127.0.0.1:8000/health` and
`Invoke-RestMethod http://127.0.0.1:8000/api/v1/system/status`, then open http://localhost:5173.

Tests: `python -m pytest tests -q` (uses a temporary database) and, in `frontend/`, `npm test` and `npm run build`.

Browser origins allowed by the API are set with `CORS_ORIGINS` in `backend/.env`.
Authentication is **off by default** (`AUTH_REQUIRED=false`); enable it before exposing the API beyond localhost.
