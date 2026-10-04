import os
import json
import numpy as np
import pandas as pd


# ============================================================
# UrbanMind AI - Ward Intervention Decision Ranking
# ============================================================

print("=" * 70)
print("UrbanMind AI - Ward Intervention Decision Ranking")
print("=" * 70)


# ============================================================
# PATHS
# ============================================================

INPUT_FILE = (
    "data/processed/ml/interventions/"
    "delhi_ward_intervention_impacts.csv"
)

OUTPUT_DIR = "data/processed/decision"

OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_decision_ranking.csv"
)

OUTPUT_SUMMARY = os.path.join(
    OUTPUT_DIR,
    "decision_ranking_summary.json"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def check_file(path, name):

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )


def check_columns(df, required_columns, name):

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{name} missing columns:\n{missing}"
        )


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_COLUMNS = [
    "Ward_No",
    "Ward_Name",
    "intervention",
    "baseline_AQI",
    "projected_AQI",
    "estimated_AQI_improvement",
    "baseline_LST_C",
    "projected_LST_C",
    "estimated_heat_reduction_C",
    "estimated_emission_reduction",
    "population",
    "child_population",
    "health_exposure_score",
    "estimated_exposure_reduction",
    "estimated_population_benefited",
    "intervention_potential",
    "impact_score",
    "intervention_rank"
]


# ============================================================
# CHECK FILE
# ============================================================

print("\nChecking required files...")

check_file(
    INPUT_FILE,
    "Intervention impact dataset"
)

print("Intervention impact dataset: FOUND")


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading intervention impact data...")

df = pd.read_csv(INPUT_FILE)

print(f"Records: {len(df)}")
print(f"Columns: {df.columns.tolist()}")

check_columns(
    df,
    REQUIRED_COLUMNS,
    "Intervention dataset"
)

print("Required column validation: PASSED")


# ============================================================
# NORMALIZE WARD IDs
# ============================================================

print("\nNormalizing Ward IDs...")

df["Ward_No"] = pd.to_numeric(
    df["Ward_No"],
    errors="coerce"
)

if df["Ward_No"].isna().any():
    raise ValueError(
        "Invalid Ward_No values found."
    )

df["Ward_No"] = df["Ward_No"].astype(int)

print("Ward ID normalization: PASSED")


# ============================================================
# INTERVENTION COVERAGE
# ============================================================

print("\nChecking intervention coverage...")

ward_count = df["Ward_No"].nunique()

intervention_count = df["intervention"].nunique()

expected_scenarios = (
    ward_count * intervention_count
)

print(f"Wards: {ward_count}")

print(
    f"Interventions: {intervention_count}"
)

print(
    f"Expected scenarios: {expected_scenarios}"
)


# ============================================================
# DUPLICATE CHECK
# ============================================================

duplicate_count = df.duplicated(
    subset=[
        "Ward_No",
        "intervention"
    ]
).sum()

print(
    f"Duplicate ward-intervention pairs: "
    f"{duplicate_count}"
)

if duplicate_count > 0:

    raise ValueError(
        "Duplicate Ward_No + intervention pairs found."
    )

print("Intervention uniqueness: PASSED")


# ============================================================
# NUMERIC VALIDATION
# ============================================================

print("\nChecking numeric values...")

NUMERIC_COLUMNS = [

    "baseline_AQI",
    "projected_AQI",
    "estimated_AQI_improvement",

    "baseline_LST_C",
    "projected_LST_C",
    "estimated_heat_reduction_C",

    "estimated_emission_reduction",

    "population",
    "child_population",

    "health_exposure_score",
    "estimated_exposure_reduction",

    "estimated_population_benefited",

    "intervention_potential",

    "impact_score",
    "intervention_rank"
]


for col in NUMERIC_COLUMNS:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )


missing_counts = (
    df[NUMERIC_COLUMNS]
    .isna()
    .sum()
)


if missing_counts.sum() > 0:

    print(
        missing_counts[
            missing_counts > 0
        ]
    )

    raise ValueError(
        "Missing or invalid numeric values found."
    )

print("Missing-value validation: PASSED")


# ============================================================
# INFINITE VALUE CHECK
# ============================================================

print("\nChecking infinite values...")

infinite_found = False


for col in NUMERIC_COLUMNS:

    count = np.isinf(
        df[col].to_numpy()
    ).sum()

    print(
        f"{col}: {count}"
    )

    if count > 0:
        infinite_found = True


if infinite_found:

    raise ValueError(
        "Infinite values found."
    )

print("Infinite-value validation: PASSED")


# ============================================================
# IMPACT SCORE VALIDATION
# ============================================================

print("\nValidating impact scores...")

if (df["impact_score"] < 0).any():

    raise ValueError(
        "Negative impact_score values found."
    )

print("Impact score validation: PASSED")


# ============================================================
# CREATE DECISION METRICS
# ============================================================

print("\nCreating decision metrics...")


# Environmental benefit

df["environmental_benefit"] = (
    df["estimated_AQI_improvement"]
    + df["estimated_heat_reduction_C"]
)


# Health benefit

df["health_benefit"] = (
    df["estimated_exposure_reduction"]
    * df["estimated_population_benefited"]
)


# Population benefit

df["population_benefit"] = (
    df["estimated_population_benefited"]
)


# Emission benefit

df["emission_benefit"] = (
    df["estimated_emission_reduction"]
)


# ============================================================
# NORMALIZATION FUNCTION
# ============================================================

def normalize_series(series):

    minimum = series.min()

    maximum = series.max()

    if maximum == minimum:

        return pd.Series(
            np.ones(len(series)),
            index=series.index
        )

    return (
        (series - minimum)
        / (maximum - minimum)
    )


# ============================================================
# NORMALIZE DECISION METRICS
# ============================================================

print(
    "Calculating normalized decision score..."
)


df["impact_score_normalized"] = (
    normalize_series(
        df["impact_score"]
    )
)


df["environmental_benefit_normalized"] = (
    normalize_series(
        df["environmental_benefit"]
    )
)


df["health_benefit_normalized"] = (
    normalize_series(
        df["health_benefit"]
    )
)


df["population_benefit_normalized"] = (
    normalize_series(
        df["population_benefit"]
    )
)


df["emission_benefit_normalized"] = (
    normalize_series(
        df["emission_benefit"]
    )
)


# ============================================================
# FINAL DECISION SCORE
# ============================================================

df["decision_score"] = (

    0.40
    * df["impact_score_normalized"]

    + 0.20
    * df["environmental_benefit_normalized"]

    + 0.20
    * df["health_benefit_normalized"]

    + 0.10
    * df["population_benefit_normalized"]

    + 0.10
    * df["emission_benefit_normalized"]
)


# ============================================================
# WARD-WISE RANKING
# ============================================================

print(
    "\nGenerating ward-wise intervention ranking..."
)


df = df.sort_values(
    [
        "Ward_No",
        "decision_score"
    ],
    ascending=[
        True,
        False
    ]
).reset_index(drop=True)


df["decision_rank"] = (

    df.groupby("Ward_No")
    ["decision_score"]
    .rank(
        method="first",
        ascending=False
    )
    .astype(int)
)


# ============================================================
# DECISION PRIORITY
# ============================================================

df["decision_priority"] = np.select(

    [
        df["decision_rank"] == 1,
        df["decision_rank"] == 2,
        df["decision_rank"] == 3
    ],

    [
        "Primary",
        "Secondary",
        "Alternative"
    ],

    default="Lower Priority"
)


# ============================================================
# PRIMARY INTERVENTION PER WARD
# ============================================================

best_interventions = (

    df[
        df["decision_rank"] == 1
    ]
    .copy()
)


# ============================================================
# VALIDATE PRIMARY COVERAGE
# ============================================================

print(
    "\nValidating ward decisions..."
)

primary_count = (
    best_interventions["Ward_No"]
    .nunique()
)


print(
    f"Wards with primary intervention: "
    f"{primary_count}"
)


if primary_count != ward_count:

    raise ValueError(
        "Every ward does not have "
        "exactly one primary intervention."
    )


print(
    "Ward decision coverage: PASSED"
)


# ============================================================
# SAVE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE CSV
# ============================================================

print(
    "\nSaving decision ranking dataset..."
)


df.to_csv(
    OUTPUT_CSV,
    index=False
)


print(
    f"CSV saved:\n{OUTPUT_CSV}"
)


# ============================================================
# CREATE SUMMARY
# ============================================================

print(
    "\nCreating decision summary..."
)


intervention_distribution = (

    best_interventions[
        "intervention"
    ]
    .value_counts()
    .to_dict()
)


summary = {

    "total_wards":
        int(ward_count),

    "total_interventions":
        int(intervention_count),

    "total_scenarios":
        int(len(df)),

    "primary_intervention_distribution":
        {
            str(key): int(value)
            for key, value
            in intervention_distribution.items()
        },

    "mean_decision_score":
        float(
            df["decision_score"].mean()
        ),

    "maximum_decision_score":
        float(
            df["decision_score"].max()
        ),

    "minimum_decision_score":
        float(
            df["decision_score"].min()
        ),

    "decision_metrics": {

        "impact_score_weight": 0.40,

        "environmental_benefit_weight": 0.20,

        "health_benefit_weight": 0.20,

        "population_benefit_weight": 0.10,

        "emission_benefit_weight": 0.10
    },

    "output_file":
        OUTPUT_CSV
}


with open(
    OUTPUT_SUMMARY,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        summary,
        file,
        indent=4
    )


print(
    f"Summary saved:\n{OUTPUT_SUMMARY}"
)


# ============================================================
# TOP WARD DECISIONS
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "TOP WARD INTERVENTION DECISIONS"
)

print(
    "=" * 70
)


display_columns = [

    "Ward_No",
    "Ward_Name",
    "intervention",

    "decision_score",
    "decision_rank",

    "estimated_AQI_improvement",

    "estimated_heat_reduction_C",

    "estimated_emission_reduction",

    "estimated_population_benefited"
]


print(

    best_interventions[
        display_columns
    ]
    .head(15)
    .to_string(
        index=False
    )

)


# ============================================================
# FINAL VALIDATION
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "FINAL DECISION RANKING VALIDATION"
)

print(
    "=" * 70
)


print(
    f"Wards: "
    f"{df['Ward_No'].nunique() == ward_count}"
)


print(
    f"Interventions: "
    f"{df['intervention'].nunique() == intervention_count}"
)


print(
    f"Scenarios: "
    f"{len(df) == expected_scenarios}"
)


print(
    f"No missing values: "
    f"{not df.isna().any().any()}"
)


numeric_df = df.select_dtypes(
    include=np.number
)


print(
    f"No infinite values: "
    f"{not np.isinf(numeric_df.to_numpy()).any()}"
)


print(
    f"Decision scores available: "
    f"{df['decision_score'].notna().all()}"
)


print(
    f"Decision ranks available: "
    f"{df['decision_rank'].notna().all()}"
)


print(
    f"Primary decision for every ward: "
    f"{primary_count == ward_count}"
)


print(
    f"CSV exists: "
    f"{os.path.exists(OUTPUT_CSV)}"
)


print(
    f"Summary exists: "
    f"{os.path.exists(OUTPUT_SUMMARY)}"
)


# ============================================================
# SUMMARY
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "DECISION RANKING SUMMARY"
)

print(
    "=" * 70
)


print(
    f"Total wards        : {ward_count}"
)

print(
    f"Total interventions: {intervention_count}"
)

print(
    f"Total scenarios    : {len(df)}"
)

print(
    f"Mean decision score: "
    f"{df['decision_score'].mean():.4f}"
)


print(
    "\nPrimary intervention distribution:"
)


for intervention, count in (
    intervention_distribution.items()
):

    print(
        f"{intervention}: "
        f"{count} wards"
    )


print(
    "\nOutput files:"
)

print(
    OUTPUT_CSV
)

print(
    OUTPUT_SUMMARY
)


print(
    "\n" + "=" * 70
)

print(
    "WARD INTERVENTION DECISION RANKING "
    "COMPLETED SUCCESSFULLY"
)

print(
    "=" * 70
)