# Phase 10 — Scenario Generation

Phase 10 converts a Phase 9 `UrbanState` plus explicit scenario-generation
options into a versioned `ScenarioSet`. The LangGraph subgraph detects
problems/objectives, retrieves Phase 7 RAG and knowledge-graph context, then
constructs and validates candidate interventions from the configurable
catalog. It does not replace or alter the Phase 9 analysis workflow.

## API

`POST /api/v1/scenarios/generate` accepts a problem/city/zone and optional
structured constraints, intervention parameters, and an existing Phase 9
`urban_state`. It returns a `ScenarioSet`.

`GET /api/v1/scenarios/{scenario_id}` retrieves an immutable scenario version.
Add `?version=2` to retrieve a particular version; without it, retrieval
returns the latest version. `POST /api/v1/scenarios/{scenario_id}/versions`
creates a new immutable version from validated parameter updates. Even after
simulation, the prior version remains unchanged; changes are stored as a new
version that requires fresh review.
`GET /api/v1/scenarios?city=Delhi&zone=Central%20Delhi` lists scenarios with
pagination.

## Catalog and validation

The default catalog includes urban forest expansion, electric bus deployment,
green-roof and cool-roof programs, traffic management, and public-transport
expansion. Add definitions through `intervention_catalog.register`. Required
implementation parameters are never fabricated: absent inputs cause
`REQUIRES_REVIEW`. Parameter, known land/time, applicability, and supplied
policy-conflict checks can mark a scenario `INVALID`. A budget limit without a
validated cost estimate also requires review.

The optional Business-as-Usual baseline contains no intervention. Scenarios
can include explicit parameter variants and a bounded number of combinations.
The generated cost and impact fields remain unset; scenario generation does
not simulate, evaluate, rank, or optimize options. Retrieved source identifiers
are retained as provenance and are not treated as proof of local impact.

## Persistence and Phase 11

Scenario requests and immutable scenario versions are stored in the existing
SQLAlchemy database (`scenario_requests` and `scenarios`). A new generation
creates version 1; parameter edits retain the scenario ID and create the next
version rather than mutating prior configurations.
Phase 11 can consume each scenario's `interventions`, parameters, target
problems, constraints, evidence IDs, workflow ID, and version. Simulation
results should be attached to that exact version by the future simulation
service, not written as Phase 10 estimates.
