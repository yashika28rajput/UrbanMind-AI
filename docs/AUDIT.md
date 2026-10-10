# UrbanMind AI – Technical audit (October 2026)

Scope of this pass: repository inspection, baseline test run, targeted fixes with regression tests.
It is **not** a complete audit of every module. Status words are used strictly:
**Fixed & verified** (test ran and passed), **Confirmed, not fixed**, **Not verified**.

## Baseline (before changes)
- Backend: 47 tests passed (Python 3.12, Linux sandbox, full dependency set). Frontend: `tsc` clean, 6 vitest tests passed, `npm run build` succeeded.
- Running the backend tests **modified a tracked file** (`models/federated/aqi_model/round_001.npz`) and wrote to the real SQLite DB.

## Fixed & verified
| # | Issue | Root cause (file) | Fix | Verified by |
|---|-------|-------------------|-----|-------------|
| 1 | Path traversal on file write | `api/federated.py` passed unvalidated `model_name` into `federated/server.py::_save_checkpoint` path | Regex-validated name; resolved path must stay under the checkpoint root | `test_federated_model_name_cannot_traverse_paths` |
| 2 | Raw exception text returned to client | `api/federated.py` returned `f"...{exc}"` | Generic message, details logged | code review + existing federated test |
| 3 | `CORS *` with credentials | `main.py` | Origins from `CORS_ORIGINS` (default localhost:5173); `*` is ignored | `test_cors_does_not_reflect_arbitrary_origins` |
| 4 | Duplicate / concurrent scenario writes reported as "storage unavailable" (503) | `phase10/repository.py` let `IntegrityError` escape | `ScenarioConflictError` (409), `ScenarioParentMissingError`; parent checked before child insert; set insert is one transaction | persistence tests (real HTTP + temp DB, no mocks) |
| 5 | Tests wrote to real DB and tracked model file | `tests/conftest.py` had no isolation | Temp `DATABASE_URL` and `URBANMIND_FEDERATED_DIR` before app import | `git status` clean after full run |
| 6 | No carbon calculation endpoint (`POST /api/v1/carbon/calculate` did not exist) | – | New `services/carbon_service.py`, `api/carbon.py`: quantity × factor, annualisation, unit-comparability check, **no built-in factors** (each activity must cite its factor) | `tests/test_carbon_calculation.py` (9 tests; 270/140/130 used only as explicit test inputs) |
| 7 | Rule-based outputs presented as model predictions | `api/predictions.py` | Responses now carry `evidence_type` and `limitations` | live call: carbon → `rule_based_estimate` |
| 8 | `requirements.txt` had a UTF-8 BOM and unconditional `pywin32` / `pywinpty` (breaks installs on non-Windows) | – | BOM removed, `sys_platform == "win32"` markers | not re-installed from scratch (see below) |

## Confirmed, NOT fixed (needs your decision or data)
1. **AQI model leakage (P2).** The target `AQI` is exactly `max(pm25_index, pm10_index, no2_index, o3_index, so2_index, co_index)` (verified on the test split) and those same-time pollutant/index columns are model features. The reported test R² 0.985 is formula reconstruction, not forecasting skill. Leak-free check I ran (lag + calendar features only, existing train/test CSVs): R² ≈ 0.657, MAE ≈ 4.16, versus **persistence baseline R² ≈ 0.663, MAE ≈ 4.22**, i.e. no demonstrated skill over "same as last hour". The model artifact and `aqi_model_info.json` were not changed; retraining and re-reporting is still required.
2. **Interpolation before splitting (P2).** `prepare_aqi_ml_dataset.py` interpolates pollutants per station with `limit_direction="both"` before the 70/15/15 chronological split, so values near split boundaries use future data. Interpolation should be fit within train only.
3. **Green cover, carbon and health "models" are formulas** (`services/prediction_service.py`; `.pkl` files are dicts) with fixed constants (e.g. 170, 150, 0.45, weights 0.35/0.30/0.20/0.15) and no data provenance. Now labelled; still not scientific evidence. Carbon should move to sourced emission factors via the new endpoint.
4. **UHI model**: 272 ward records from one city, random-split risk and no spatial cross-validation. Not re-evaluated.
5. **Simulations can be orphaned**: `simulations.scenario_id` has no foreign key and `/simulation/run` accepts any scenario payload. Needs a composite FK `(scenario_id, scenario_version)` plus a migration (Alembic is in requirements but no migrations exist; `create_all` does not alter existing tables). Not changed to avoid a schema/API break.
6. **Authentication is off by default** (`AUTH_REQUIRED=false`), so all write endpoints are open. Auth code exists (PBKDF2 + hand-rolled HS256 JWT); consider a maintained JWT library. Not changed.
7. **Federated learning** runs a Flower *simulation* on one machine over the same dataset; this is not deployed multi-party federated learning.
8. **RAG** falls back to a non-persistent mode when Qdrant is not configured (`/system/status` reports `rag: DEGRADED`).
9. `initialize_database()` runs `create_all` on every repository call (works, wasteful).
10. No frontend test covers the carbon endpoint (the dashboard does not call it yet).

## Not verified
- Windows/PowerShell run (commands in README are untested on Windows; I ran on Linux).
- Fresh `pip install -r backend/requirements.txt` (I installed only the packages the code imports; `torch`, `jupyter` etc. in requirements are not imported by `backend/app`).
- scikit-learn artifact compatibility: the pickled AQI/UHI models loaded and predicted under the sandbox's scikit-learn; the pinned `scikit-learn==1.9.0` was not tested.
- Large-file/Git-history state (shallow clone only). `.gitignore` lists the four large files; none are tracked at HEAD.
- Dashboard click-through in a browser; only the 6 existing vitest tests were run.

## Test results (this environment)
- Backend: **67 passed, 0 failed** (47 original + 20 new).
- Frontend: typecheck clean, **6/6** vitest, production build OK (unchanged code).
