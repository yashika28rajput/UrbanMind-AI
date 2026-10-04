import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd


# ============================================================
# UrbanMind AI - Explainable Decision Layer
# ============================================================

print("=" * 70)
print("UrbanMind AI - Explainable Decision Layer")
print("=" * 70)


# ============================================================
# FILE PATHS
# ============================================================

DECISION_FILE = (
    "data/processed/decision/delhi_ward_decision_ranking.geojson"
)

ENVIRONMENT_FILE = (
    "data/processed/ml/environmental/"
    "delhi_ward_environmental_risk.csv"
)

HEALTH_FILE = (
    "data/processed/ml/health/"
    "delhi_ward_health_impact.csv"
)

OUTPUT_DIR = "data/processed/decision"

OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_decision_explanations.csv"
)

OUTPUT_GEOJSON = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_decision_explanations.geojson"
)

OUTPUT_SUMMARY = os.path.join(
    OUTPUT_DIR,
    "decision_explanation_summary.json"
)


# ============================================================
# HELPERS
# ============================================================

def check_file(path, name):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )

    print(f"{name}: FOUND")


def clean_numeric(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

    return df


# ============================================================
# CHECK REQUIRED FILES
# ============================================================

print("\nChecking required files...")

check_file(
    DECISION_FILE,
    "Decision ranking layer"
)

check_file(
    ENVIRONMENT_FILE,
    "Environmental risk layer"
)

check_file(
    HEALTH_FILE,
    "Health impact layer"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading decision data...")

decision = gpd.read_file(
    DECISION_FILE
)

print(
    f"Decision records: {len(decision)}"
)


print("\nLoading environmental data...")

environment = pd.read_csv(
    ENVIRONMENT_FILE
)

print(
    f"Environmental records: {len(environment)}"
)


print("\nLoading health data...")

health = pd.read_csv(
    HEALTH_FILE
)

print(
    f"Health records: {len(health)}"
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

decision_required = [
    "Ward_No",
    "Ward_Name",
    "intervention",
    "decision_score",
    "global_rank",
    "ward_rank",
    "recommended",
    "decision_label",
    "estimated_heat_reduction_C",
    "estimated_emission_reduction",
    "geometry"
]

environment_required = [
    "Ward_No",
    "final_AQI",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score"
]

health_required = [
    "Ward_No",
    "TOT_P",
    "children_percent",
    "health_exposure_score",
    "population_vulnerability_index",
    "population_weighted_environmental_burden"
]


for col in decision_required:
    if col not in decision.columns:
        raise ValueError(
            f"Missing decision column: {col}"
        )


for col in environment_required:
    if col not in environment.columns:
        raise ValueError(
            f"Missing environmental column: {col}"
        )


for col in health_required:
    if col not in health.columns:
        raise ValueError(
            f"Missing health column: {col}"
        )


print("Required column validation: PASSED")


# ============================================================
# NORMALIZE WARD IDS
# ============================================================

print("\nNormalizing Ward IDs...")

decision["Ward_No"] = pd.to_numeric(
    decision["Ward_No"],
    errors="coerce"
)

environment["Ward_No"] = pd.to_numeric(
    environment["Ward_No"],
    errors="coerce"
)

health["Ward_No"] = pd.to_numeric(
    health["Ward_No"],
    errors="coerce"
)

if (
    decision["Ward_No"].isna().any()
    or environment["Ward_No"].isna().any()
    or health["Ward_No"].isna().any()
):
    raise ValueError(
        "Invalid Ward_No values found."
    )

decision["Ward_No"] = decision["Ward_No"].astype(int)
environment["Ward_No"] = environment["Ward_No"].astype(int)
health["Ward_No"] = health["Ward_No"].astype(int)

print("Ward ID normalization: PASSED")


# ============================================================
# SELECT RECOMMENDED DECISIONS
# ============================================================

print("\nSelecting recommended decisions...")

recommended = decision[
    decision["recommended"] == True
].copy()

print(
    f"Recommended decisions: {len(recommended)}"
)

unique_wards = recommended["Ward_No"].nunique()

print(
    f"Unique recommended wards: {unique_wards}"
)

if len(recommended) != 272:
    raise ValueError(
        "Expected exactly 272 recommended ward decisions."
    )

if unique_wards != 272:
    raise ValueError(
        "Every ward must have exactly one recommendation."
    )

duplicate_recommendations = (
    recommended["Ward_No"]
    .duplicated()
    .sum()
)

if duplicate_recommendations != 0:
    raise ValueError(
        "Duplicate recommended decisions found."
    )

print(
    "Recommended decision validation: PASSED"
)


# ============================================================
# SELECT ENVIRONMENT + HEALTH DATA
# ============================================================

environment_cols = [
    "Ward_No",
    "final_AQI",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score"
]

health_cols = [
    "Ward_No",
    "TOT_P",
    "children_percent",
    "health_exposure_score",
    "population_vulnerability_index",
    "population_weighted_environmental_burden"
]

environment = environment[
    environment_cols
].copy()

health = health[
    health_cols
].copy()


# ============================================================
# MERGE
# ============================================================

print("\nMerging decision + environmental + health data...")

result = recommended.merge(
    environment,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)

result = result.merge(
    health,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)

print(
    f"Records after merge: {len(result)}"
)

if len(result) != 272:
    raise ValueError(
        "Final decision records should contain 272 wards."
    )

print("Decision merge: PASSED")


# ============================================================
# NUMERIC CLEANING
# ============================================================

numeric_columns = [
    "decision_score",
    "global_rank",
    "ward_rank",
    "estimated_heat_reduction_C",
    "estimated_emission_reduction",
    "final_AQI",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score",
    "TOT_P",
    "children_percent",
    "health_exposure_score",
    "population_vulnerability_index",
    "population_weighted_environmental_burden"
]

result = clean_numeric(
    result,
    numeric_columns
)


# ============================================================
# MISSING VALUE CHECK
# ============================================================

print("\nChecking missing values...")

missing = result[numeric_columns].isna().sum()

missing = missing[
    missing > 0
]

if len(missing) > 0:
    print(missing)
    raise ValueError(
        "Missing values found in explanation indicators."
    )

print("Missing-value validation: PASSED")


# ============================================================
# INFINITE VALUE CHECK
# ============================================================

print("\nChecking infinite values...")

for col in numeric_columns:

    count = np.isinf(
        result[col].to_numpy()
    ).sum()

    print(
        f"{col}: {count}"
    )

    if count > 0:
        raise ValueError(
            f"Infinite values found in {col}"
        )

print("Infinite-value validation: PASSED")


# ============================================================
# CREATE EXPLANATION COMPONENTS
# ============================================================

print("\nCreating explanation components...")


def risk_level(value):
    if value >= 0.70:
        return "High"
    elif value >= 0.40:
        return "Moderate"
    else:
        return "Low"


result["AQI_risk_level"] = result[
    "AQI_risk_index"
].apply(risk_level)

result["heat_risk_level"] = result[
    "heat_risk_index"
].apply(risk_level)

result["emission_risk_level"] = result[
    "emission_risk_index"
].apply(risk_level)

result["traffic_risk_level"] = result[
    "traffic_risk_index"
].apply(risk_level)

result["vegetation_risk_level"] = result[
    "vegetation_risk_index"
].apply(risk_level)


# ============================================================
# MAIN DECISION REASON
# ============================================================

def create_reason(row):

    reasons = []

    if row["AQI_risk_index"] >= 0.40:
        reasons.append(
            "air-pollution risk"
        )

    if row["heat_risk_index"] >= 0.40:
        reasons.append(
            "heat risk"
        )

    if row["emission_risk_index"] >= 0.40:
        reasons.append(
            "emission pressure"
        )

    if row["traffic_risk_index"] >= 0.40:
        reasons.append(
            "traffic pressure"
        )

    if row["vegetation_risk_index"] >= 0.40:
        reasons.append(
            "vegetation-related environmental pressure"
        )

    if not reasons:
        reasons.append(
            "combined environmental conditions"
        )

    return (
        "Recommended based on "
        + ", ".join(reasons)
        + "."
    )


result["decision_reason"] = result.apply(
    create_reason,
    axis=1
)


# ============================================================
# IMPACT SUMMARY
# ============================================================

def create_impact_summary(row):

    return (
        f"Expected heat reduction: "
        f"{row['estimated_heat_reduction_C']:.2f} °C; "
        f"estimated emission reduction: "
        f"{row['estimated_emission_reduction']:.3f}."
    )


result["expected_impact_summary"] = result.apply(
    create_impact_summary,
    axis=1
)


# ============================================================
# HUMAN-READABLE EXPLANATION
# ============================================================

def create_explanation(row):

    return (
        f"{row['intervention']} is recommended for "
        f"Ward {int(row['Ward_No'])} ({row['Ward_Name']}). "
        f"The decision score is "
        f"{row['decision_score']:.3f}. "
        f"The ward has an environmental risk score of "
        f"{row['environmental_risk_score']:.3f} "
        f"and a health exposure score of "
        f"{row['health_exposure_score']:.2f}. "
        f"{row['decision_reason']} "
        f"{row['expected_impact_summary']}"
    )


result["decision_explanation"] = result.apply(
    create_explanation,
    axis=1
)


# ============================================================
# VALIDATE EXPLANATIONS
# ============================================================

print("\nValidating explanations...")

if result["decision_reason"].isna().any():
    raise ValueError(
        "Missing decision reasons."
    )

if result["decision_explanation"].isna().any():
    raise ValueError(
        "Missing decision explanations."
    )

if (
    result["decision_explanation"]
    .astype(str)
    .str.len()
    .eq(0)
    .any()
):
    raise ValueError(
        "Empty decision explanations found."
    )

print(
    "Explanation validation: PASSED"
)


# ============================================================
# SAVE CSV
# ============================================================

print("\nSaving decision explanations CSV...")

csv_columns = [
    "Ward_No",
    "Ward_Name",
    "intervention",
    "decision_score",
    "global_rank",
    "ward_rank",
    "decision_label",
    "final_AQI",
    "AQI_risk_level",
    "AQI_risk_index",
    "heat_risk_level",
    "heat_risk_index",
    "emission_risk_level",
    "emission_risk_index",
    "traffic_risk_level",
    "traffic_risk_index",
    "vegetation_risk_level",
    "vegetation_risk_index",
    "environmental_risk_score",
    "TOT_P",
    "children_percent",
    "health_exposure_score",
    "population_vulnerability_index",
    "population_weighted_environmental_burden",
    "estimated_heat_reduction_C",
    "estimated_emission_reduction",
    "decision_reason",
    "expected_impact_summary",
    "decision_explanation"
]

result[csv_columns].to_csv(
    OUTPUT_CSV,
    index=False
)

print(
    f"CSV saved:\n{OUTPUT_CSV}"
)


# ============================================================
# SAVE GEOJSON
# ============================================================

print("\nSaving decision explanations GeoJSON...")

geojson_columns = [
    col for col in csv_columns
    if col in result.columns
]

geojson_result = result[
    geojson_columns + ["geometry"]
].copy()

geojson_result.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)

print(
    f"GeoJSON saved:\n{OUTPUT_GEOJSON}"
)


# ============================================================
# SUMMARY
# ============================================================

intervention_distribution = (
    result["intervention"]
    .value_counts()
    .to_dict()
)

summary = {
    "total_wards": int(
        result["Ward_No"].nunique()
    ),
    "recommended_decisions": int(
        len(result)
    ),
    "mean_decision_score": float(
        result["decision_score"].mean()
    ),
    "mean_environmental_risk": float(
        result["environmental_risk_score"].mean()
    ),
    "mean_health_exposure": float(
        result["health_exposure_score"].mean()
    ),
    "mean_AQI": float(
        result["final_AQI"].mean()
    ),
    "intervention_distribution":
        intervention_distribution,
    "explanation_records": int(
        len(result)
    ),
    "outputs": {
        "csv": OUTPUT_CSV,
        "geojson": OUTPUT_GEOJSON,
        "summary": OUTPUT_SUMMARY
    }
}

with open(
    OUTPUT_SUMMARY,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        summary,
        f,
        indent=4
    )

print(
    f"Summary saved:\n{OUTPUT_SUMMARY}"
)


# ============================================================
# SAMPLE OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("SAMPLE DECISION EXPLANATIONS")
print("=" * 70)

display_columns = [
    "Ward_No",
    "Ward_Name",
    "intervention",
    "decision_score",
    "decision_reason",
    "decision_explanation"
]

print(
    result[display_columns]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL DECISION EXPLANATION VALIDATION")
print("=" * 70)

print(
    f"Wards: "
    f"{result['Ward_No'].nunique() == 272}"
)

print(
    f"Recommended decisions: "
    f"{len(result) == 272}"
)

print(
    f"Decision scores available: "
    f"{result['decision_score'].notna().all()}"
)

print(
    f"Environmental risk available: "
    f"{result['environmental_risk_score'].notna().all()}"
)

print(
    f"Health exposure available: "
    f"{result['health_exposure_score'].notna().all()}"
)

print(
    f"Explanations available: "
    f"{result['decision_explanation'].notna().all()}"
)

print(
    f"Geometry available: "
    f"{result.geometry.notna().all()}"
)

print(
    f"CSV exists: "
    f"{os.path.exists(OUTPUT_CSV)}"
)

print(
    f"GeoJSON exists: "
    f"{os.path.exists(OUTPUT_GEOJSON)}"
)

print(
    f"Summary exists: "
    f"{os.path.exists(OUTPUT_SUMMARY)}"
)


print("\n" + "=" * 70)
print(
    "EXPLAINABLE DECISION LAYER COMPLETED SUCCESSFULLY"
)
print("=" * 70)