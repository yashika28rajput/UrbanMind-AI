# Phases 11–13 — Simulation, Optimization, and Explainability

These services extend Phase 10 scenarios and reuse the Phase 4 prediction
service, Phase 9 `UrbanState`, Phase 10 `Scenario` and provenance-validated
impact/cost estimates, SQLAlchemy database, and LangGraph. They do not change
the Phase 10 generation endpoint or the Phase 9 analysis workflow.

## Phase 11: Digital Twin simulation

`POST /api/v1/simulation/run` accepts an existing `UrbanState`, one Phase 10
`Scenario`, and optional baseline/model inputs. The result includes before and
after states and one `MetricDelta` per supported metric. A generated Phase 10
scenario can be sent directly as the `scenario` object.

Metrics include AQI, temperature/UHI, green cover, carbon reduction and
emissions, health risk/benefit, cost, population exposure, execution time, and
sustainability. Model values are calculated with the existing trained AQI and
urban-heat estimators, or the existing formula-based green-cover and health
estimators, only when the corresponding model features are supplied. The
checked-in carbon artifact is a rule-based placeholder, not a calibrated
tCO2e estimator; carbon reduction remains unavailable unless a provenance-backed
impact estimate is supplied.
Feature names must match the model metadata. Scenario feature overrides can be
given globally for a one-scenario request, by generated scenario ID, or by
intervention ID (use the latter for a set of generated scenarios).

For example, provide baseline features under `model_features` and a changed
feature vector under `scenario_features_by_intervention: {
"urban_forest_expansion": {"green_cover": {...}} }`. Per-scenario overrides
take precedence over intervention-level overrides, which take precedence over
the global `scenario_model_features`. External validated impacts such as
population exposure or a sustainability score can be included in
`scenario_estimates`; each value carries its own source and unit.

Phase 10 expected-impact estimates are used only when they pass its
provenance validation. External metrics can be supplied as
`scenario_estimates` with source, source type, units, and optional model
version/confidence/uncertainty. If neither model input nor a provenance-backed
estimate is available, the output metric is marked unavailable; the simulator
does not assume a zero impact or invent an impact coefficient. Confidence
remains unset unless supplied by an actual estimator. AQI/UHI model evaluation
MAE is reported as error, not as a confidence interval.

When a model prediction is unavailable but a numeric baseline and a Phase 10
provenance-backed delta exist, the isolated fallback applies `simulated =
baseline + validated_delta`. A Phase 10 carbon-reduction estimate is itself an
absolute reduction metric and can be reported without a separate baseline
carbon-impact value; this does not make baseline carbon emissions available.
The API relies on the supplied estimate's provenance declaration and does not
independently validate external evidence. It does not extrapolate a generic
intervention coefficient. Other derived metrics remain unavailable when their
required baseline or validated delta is missing.

The normalized request has a SHA-256 reproducibility key. Simulation records,
including the scenario ID/version, are stored in the existing configured
database (`simulations` table).

`GET /api/v1/simulation/{simulation_id}` retrieves a persisted result.

## Phase 12: multi-objective optimization

`POST /api/v1/optimization/run` accepts Phase 11 results, objective names and
directions, optional objective weights, and constraints. The implementation
uses NSGA-II non-dominated sorting and crowding distance over the supplied
finite set of simulated scenarios; it does not invent or mutate intervention
parameters. Pareto solutions, dominated feasible strategies, infeasible
strategies, missing objective values, and constraint violations are retained
separately. A candidate missing any requested objective is not treated as
feasible. Crowd-boundary solutions have `crowding_boundary: true`; their
unbounded crowding distance is represented as JSON `null`.

Optional decision preferences (or objective weights) are applied only after
the Pareto frontier is calculated. Without preferences, the API preserves the
frontier and does not pick a single winner. Supported constraints are numeric
`<=`/`>=` comparisons, including budget, green-cover improvement, duration,
and externally defined policy/feasibility metrics.

`GET /api/v1/optimization/{optimization_id}` retrieves a persisted result from
the existing configured database (`optimization_runs` table).

## Phase 13: explanations and counterfactuals

- `POST /api/v1/explain/prediction` uses Tree SHAP for the trained AQI/UHI
  Gradient Boosting estimators. The existing formula-based green-cover,
  carbon, and health estimators use permutation SHAP and require
  `background_features` from the caller.
- `POST /api/v1/explain/counterfactual` changes exactly one named model input,
  reruns the corresponding Phase 4 prediction function, and returns the
  baseline/counterfactual values and delta.
- `POST /api/v1/explain/recommendation` derives reasons and tradeoffs from
  supplied simulation deltas and Pareto objective directions. It does not
  generate hard-coded reasons or select a preferred strategy when no
  decision score exists.

Model confidence is not fabricated. Reported test-set MAE/RMSE is exposed as
evaluation uncertainty where model metadata provides it. Tree and permutation
SHAP results use the model or supplied background data, respectively.

## Complete LangGraph pipeline

`POST /api/v1/pipeline/run` executes these nodes in order:

`Phase 10 scenario generation → Phase 11 simulation → Phase 12 Pareto
optimization → Phase 13 recommendation explanation → final decision report`

It accepts the Phase 10 generation request plus `simulation_input`,
`optimization_objectives`, `optimization_constraints`, and
`decision_preferences`. Generated scenarios, simulations, and optimization
runs are persisted. Invalid Phase 10 scenarios are not simulated; scenarios
with unresolved required parameters can be simulated only to the extent that
their supplied metric/model inputs allow, and missing results remain
infeasible for optimization.

### Run locally (PowerShell)

From the `UrbanMind-AI` project directory, start the API:

```powershell
$env:PYTHONPATH = "$PWD\backend"
& "..\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another PowerShell window in the same project directory, submit a small
green-cover pipeline request (the candidate feature values are planner/model
inputs; they are not generated by an LLM):

```powershell
$body = @'
{
  "city": "TestCity",
  "zone": "Ward 1",
  "problem_statement": "Low green cover",
  "problems": ["low_green_cover"],
  "requested_interventions": ["Urban Forest Expansion"],
  "intervention_parameters": {
    "urban_forest_expansion": {"area_hectares": 2, "tree_density": 100}
  },
  "simulation_input": {
    "model_features": {
      "green_cover": {
        "trees": 0.1,
        "grass": 0,
        "flooded_vegetation": 0,
        "crops": 0,
        "shrub_and_scrub": 0,
        "vegetation": 0.1,
        "built": 0.5
      }
    },
    "scenario_features_by_intervention": {
      "urban_forest_expansion": {
        "green_cover": {
          "trees": 0.2,
          "vegetation": 0.2,
          "built": 0.5
        }
      }
    }
  },
  "optimization_objectives": [
    {"name": "green_cover", "direction": "maximize", "weight": 1}
  ],
  "decision_preferences": {"green_cover": 1}
}
'@
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/pipeline/run" -ContentType "application/json" -Body $body
```

To run the complete test suite:

```powershell
$env:PYTHONPATH = "$PWD\backend"
& "..\.venv\Scripts\python.exe" -m pytest tests -q
```
# Carbon scenario input workflow

Scenario Lab also exposes a transport carbon comparison at
`POST /api/v1/carbon/scenarios/calculate`. It compares annual diesel baseline
emissions with annual charging-electricity emissions for the same explicitly
entered vehicle-kilometres:

- Baseline tCO2/year = vehicle-km/year × diesel litres/vehicle-km × kg CO2/litre ÷ 1,000.
- Project tCO2/year = vehicle-km/year × electric kWh/vehicle-km × kg CO2/kWh ÷ 1,000.
- Avoided tCO2/year = baseline minus project; the result can be negative.

The UI starts with clearly labelled illustrative assumptions, and the API
returns those results as `SIMULATED` with `SIMULATED SCENARIO — NOT MEASURED`.
Estimated and measured classifications require non-demo activity provenance;
measured additionally requires both factors to be marked verified. These are
user-declared references, not independently validated source integrations.
Each reporting period must cover one annual interval, and the baseline must
precede the project period. Each calculated scenario is saved through the
existing Phase 10 scenario repository with its input and calculation
provenance; its carbon estimate is not copied into `expected_impacts` and is
not propagated into city, ward, or Digital Twin metrics. This pilot reports
CO2, not full CO2e, and does not establish actual fleet activity, factor
authority, or achieved impacts.
