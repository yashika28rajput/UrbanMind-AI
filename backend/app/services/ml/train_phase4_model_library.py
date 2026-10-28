import json
from pathlib import Path

import joblib
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[4]
MODELS_DIR = ROOT_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


green_cover_model = {
    "type": "green_cover",
    "description": "Rule-based green cover estimator derived from land-use shares.",
}
carbon_model = {
    "type": "carbon_reduction",
    "description": "Rule-based carbon reduction estimator based on green cover and emissions.",
}
health_model = {
    "type": "health_risk",
    "description": "Rule-based exposure score combining AQI, heat, and vulnerable population burden.",
}

joblib.dump(green_cover_model, MODELS_DIR / "green_cover_model.pkl")
joblib.dump(carbon_model, MODELS_DIR / "carbon_model.pkl")
joblib.dump(health_model, MODELS_DIR / "health_risk_model.pkl")

with (MODELS_DIR / "green_cover_model_info.json").open("w", encoding="utf-8") as handle:
    json.dump(
        {
            "model_name": "Green Cover Estimator",
            "target": "green_cover_percent",
            "features": [
                "trees",
                "grass",
                "flooded_vegetation",
                "crops",
                "shrub_and_scrub",
                "vegetation",
                "built",
            ],
            "unit": "%",
        },
        handle,
        indent=2,
    )

with (MODELS_DIR / "carbon_model_info.json").open("w", encoding="utf-8") as handle:
    json.dump(
        {
            "model_name": "Carbon Reduction Estimator",
            "target": "CO2_reduction_tons",
            "features": [
                "green_cover_percent",
                "emission_pressure_index",
                "intervention_strength",
                "urban_intervention_potential",
            ],
            "unit": "tCO2e/year",
        },
        handle,
        indent=2,
    )

with (MODELS_DIR / "health_risk_model_info.json").open("w", encoding="utf-8") as handle:
    json.dump(
        {
            "model_name": "Health Risk Estimator",
            "target": "health_risk_score",
            "features": [
                "AQI_risk_index",
                "heat_risk_index",
                "population_vulnerability_index",
                "health_exposure_score",
            ],
            "unit": "composite score (0–100)",
        },
        handle,
        indent=2,
    )

print("Saved phase 4 model library to:", MODELS_DIR)
print("Created:")
for name in [
    "green_cover_model.pkl",
    "green_cover_model_info.json",
    "carbon_model.pkl",
    "carbon_model_info.json",
    "health_risk_model.pkl",
    "health_risk_model_info.json",
]:
    print(" -", name)
