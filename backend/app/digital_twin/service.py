import json
from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]
DIGITAL_TWIN_DIR = Path(__file__).resolve().parent
ENVIRONMENT_FILE = BASE_DIR / "data" / "processed" / "ml" / "environmental" / "delhi_ward_environmental_risk.csv"
HEALTH_FILE = BASE_DIR / "data" / "processed" / "ml" / "health" / "delhi_ward_health_impact.csv"
SNAPSHOT_PATH = DIGITAL_TWIN_DIR / "delhi_virtual_city_model.json"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _extract_ward_metrics() -> list[dict[str, Any]]:
    environment = pd.read_csv(ENVIRONMENT_FILE)
    health = pd.read_csv(HEALTH_FILE)

    common_columns = ["Ward_No", "Ward_Name"]
    environment = environment.copy()
    health = health.copy()

    for frame in (environment, health):
        frame["Ward_No"] = pd.to_numeric(frame["Ward_No"], errors="coerce")
        frame["Ward_No"] = frame["Ward_No"].astype("Int64")

    merged = environment.merge(
        health[common_columns + ["TOT_P", "health_exposure_score", "population_vulnerability_index"]],
        on=["Ward_No", "Ward_Name"],
        how="left",
    )

    if merged.empty:
        raise ValueError("No digital twin ward data available.")

    states: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        ward_no = int(row["Ward_No"])
        ward_name = str(row.get("Ward_Name", f"Ward_{ward_no}"))
        aqi = _safe_float(row.get("final_AQI"), 0.0)
        temperature = _safe_float(row.get("mean_LST_C"), 0.0)
        vegetation_risk = _safe_float(row.get("vegetation_risk_index"), 0.0)
        traffic_density = _safe_float(row.get("traffic_risk_index", row.get("traffic_pressure_index")), 0.0)
        green_cover = max(0.0, min(100.0, 100.0 - (vegetation_risk * 100.0)))
        health_risk = min(1.0, max(0.0, _safe_float(row.get("health_exposure_score"), 0.0) / 100.0))
        population = _safe_float(row.get("TOT_P"), 0.0)

        states.append(
            {
                "city": "Delhi",
                "zone": f"Ward_{ward_no}",
                "location": ward_name,
                "ward_no": ward_no,
                "aqi": round(aqi, 2),
                "temperature": round(temperature, 2),
                "green_cover": round(green_cover, 2),
                "traffic_density": round(traffic_density, 4),
                "health_risk": round(health_risk, 4),
                "population": int(population),
            }
        )

    return states


def build_virtual_city_model() -> dict[str, Any]:
    states = _extract_ward_metrics()
    if not states:
        raise ValueError("Digital twin model is empty.")

    summary = {
        "city": "Delhi",
        "phase": "PHASE 5 — Urban Digital Twin",
        "zone_count": len(states),
        "average_aqi": round(sum(item["aqi"] for item in states) / len(states), 2),
        "average_temperature_c": round(sum(item["temperature"] for item in states) / len(states), 2),
        "average_green_cover_pct": round(sum(item["green_cover"] for item in states) / len(states), 2),
        "average_traffic_density": round(sum(item["traffic_density"] for item in states) / len(states), 4),
        "average_health_risk": round(sum(item["health_risk"] for item in states) / len(states), 4),
    }

    model = {
        "city": "Delhi",
        "phase": "PHASE 5 — Urban Digital Twin",
        "digital_twin_type": "virtual_city_model",
        "summary": summary,
        "wards": states,
    }

    with SNAPSHOT_PATH.open("w", encoding="utf-8") as file:
        json.dump(model, file, indent=2)

    return model


def get_virtual_city_model() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        return build_virtual_city_model()

    with SNAPSHOT_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_ward_state(ward_no: int) -> dict[str, Any]:
    model = get_virtual_city_model()
    for ward in model["wards"]:
        if ward["ward_no"] == int(ward_no):
            return ward
    raise KeyError(f"Ward {ward_no} not found in the digital twin model.")
