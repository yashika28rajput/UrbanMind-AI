import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = "data/processed"

DECISION_FILE = (
    f"{BASE_DIR}/decision/"
    f"delhi_ward_decision_explanations.csv"
)

ENVIRONMENT_FILE = (
    f"{BASE_DIR}/ml/environmental/"
    f"delhi_ward_environmental_risk.csv"
)

HEALTH_FILE = (
    f"{BASE_DIR}/ml/health/"
    f"delhi_ward_health_impact.csv"
)

GEOMETRY_FILE = (
    f"{BASE_DIR}/ml/environmental/"
    f"delhi_ward_environmental_risk.geojson"
)

OUTPUT_DIR = f"{BASE_DIR}/decision"

OUTPUT_CSV = (
    f"{OUTPUT_DIR}/delhi_ward_final_decisions.csv"
)

OUTPUT_GEOJSON = (
    f"{OUTPUT_DIR}/delhi_ward_final_decisions.geojson"
)

OUTPUT_SUMMARY = (
    f"{OUTPUT_DIR}/final_decision_summary.json"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def check_file(path, name):

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )

    print(f"{name}: FOUND")


def normalize_ward_id(df, column="Ward_No"):

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    return df


def check_duplicates(df, name):

    duplicates = df["Ward_No"].duplicated().sum()

    print(
        f"{name} duplicates: {duplicates}"
    )

    if duplicates > 0:

        raise ValueError(
            f"Duplicate Ward_No found in {name}"
        )


def check_numeric(df, columns):

    for column in columns:

        if column not in df.columns:

            raise ValueError(
                f"Missing numeric column: {column}"
            )

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        missing = df[column].isna().sum()

        if missing > 0:

            raise ValueError(
                f"Invalid/missing values in {column}: "
                f"{missing}"
            )

        infinite = np.isinf(
            df[column].to_numpy(dtype=float)
        ).sum()

        if infinite > 0:

            raise ValueError(
                f"Infinite values found in {column}"
            )


# ============================================================
# START
# ============================================================

print("=" * 70)
print("UrbanMind AI - Final Ward Decision Layer")
print("=" * 70)


# ============================================================
# CHECK REQUIRED FILES
# ============================================================

print("\nChecking required files...")

check_file(
    DECISION_FILE,
    "Decision explanation layer"
)

check_file(
    ENVIRONMENT_FILE,
    "Environmental risk layer"
)

check_file(
    HEALTH_FILE,
    "Health impact layer"
)

check_file(
    GEOMETRY_FILE,
    "Ward geometry"
)


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading decision data...")

decision_df = pd.read_csv(
    DECISION_FILE
)

print(
    f"Decision records: {len(decision_df)}"
)

print(
    f"Decision columns: "
    f"{decision_df.columns.tolist()}"
)


print("\nLoading environmental data...")

environment_df = pd.read_csv(
    ENVIRONMENT_FILE
)

print(
    f"Environmental records: "
    f"{len(environment_df)}"
)


print("\nLoading health data...")

health_df = pd.read_csv(
    HEALTH_FILE
)

print(
    f"Health records: "
    f"{len(health_df)}"
)


# ============================================================
# REQUIRED COLUMNS
# ============================================================

print("\nChecking required columns...")


decision_columns = [

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


environment_columns = [

    "Ward_No",

    "final_AQI",

    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",

    "environmental_risk_score"
]


health_columns = [

    "Ward_No",

    "TOT_P",
    "children_percent",

    "health_exposure_score",

    "population_vulnerability_index",

    "population_weighted_environmental_burden"
]


for column in decision_columns:

    if column not in decision_df.columns:

        raise ValueError(
            f"Missing decision column: {column}"
        )


for column in environment_columns:

    if column not in environment_df.columns:

        raise ValueError(
            f"Missing environmental column: {column}"
        )


for column in health_columns:

    if column not in health_df.columns:

        raise ValueError(
            f"Missing health column: {column}"
        )


print(
    "Required column validation: PASSED"
)


# ============================================================
# NORMALIZE WARD IDS
# ============================================================

print("\nNormalizing Ward IDs...")

decision_df = normalize_ward_id(
    decision_df
)

environment_df = normalize_ward_id(
    environment_df
)

health_df = normalize_ward_id(
    health_df
)


# Remove invalid Ward IDs

decision_df = decision_df[
    decision_df["Ward_No"].notna()
].copy()

environment_df = environment_df[
    environment_df["Ward_No"].notna()
].copy()

health_df = health_df[
    health_df["Ward_No"].notna()
].copy()


decision_df["Ward_No"] = (
    decision_df["Ward_No"].astype(int)
)

environment_df["Ward_No"] = (
    environment_df["Ward_No"].astype(int)
)

health_df["Ward_No"] = (
    health_df["Ward_No"].astype(int)
)


print(
    "Ward ID normalization: PASSED"
)


# ============================================================
# SELECT RECOMMENDED DECISIONS
# ============================================================

print(
    "\nSelecting recommended decisions..."
)


# ward_rank = 1 means primary recommendation

recommended = decision_df[
    decision_df["ward_rank"] == 1
].copy()


print(
    f"Recommended decisions: "
    f"{len(recommended)}"
)


unique_wards = (
    recommended["Ward_No"].nunique()
)


print(
    f"Unique recommended wards: "
    f"{unique_wards}"
)


if unique_wards != 272:

    raise ValueError(
        "Recommended decision layer does not "
        "contain exactly 272 unique wards."
    )


print(
    "Recommended decision validation: PASSED"
)


# ============================================================
# DUPLICATE VALIDATION
# ============================================================

print(
    "\nChecking duplicate wards..."
)

check_duplicates(
    recommended,
    "Recommended decisions"
)

check_duplicates(
    environment_df,
    "Environmental data"
)

check_duplicates(
    health_df,
    "Health data"
)

print(
    "Duplicate validation: PASSED"
)


# ============================================================
# MERGE ENVIRONMENTAL + HEALTH DATA
# ============================================================

print(
    "\nMerging environmental + health data..."
)


final_df = recommended.merge(

    environment_df[
        environment_columns
    ],

    on="Ward_No",

    how="inner",

    suffixes=(
        "",
        "_environment"
    ),

    validate="one_to_one"
)


final_df = final_df.merge(

    health_df[
        health_columns
    ],

    on="Ward_No",

    how="inner",

    suffixes=(
        "",
        "_health"
    ),

    validate="one_to_one"
)


print(
    f"Records after merge: "
    f"{len(final_df)}"
)


if len(final_df) != 272:

    raise ValueError(
        "Final merge does not contain "
        "all 272 wards."
    )


print(
    "Environmental + health merge: PASSED"
)


# ============================================================
# REMOVE DUPLICATE SUFFIX COLUMNS
# ============================================================

if "final_AQI_environment" in final_df.columns:

    final_df = final_df.drop(
        columns=[
            "final_AQI_environment"
        ]
    )


if "AQI_risk_index_environment" in final_df.columns:

    final_df = final_df.drop(
        columns=[
            "AQI_risk_index_environment"
        ]
    )


if "heat_risk_index_environment" in final_df.columns:

    final_df = final_df.drop(
        columns=[
            "heat_risk_index_environment"
        ]
    )


if "emission_risk_index_environment" in final_df.columns:

    final_df = final_df.drop(
        columns=[
            "emission_risk_index_environment"
        ]
    )


if "traffic_risk_index_environment" in final_df.columns:

    final_df = final_df.drop(
        columns=[
            "traffic_risk_index_environment"
        ]
    )


if "vegetation_risk_index_environment" in final_df.columns:

    final_df = final_df.drop(
        columns=[
            "vegetation_risk_index_environment"
        ]
    )


if "environmental_risk_score_environment" in final_df.columns:

    final_df = final_df.drop(
        columns=[
            "environmental_risk_score_environment"
        ]
    )


# ============================================================
# NUMERIC VALIDATION
# ============================================================

print(
    "\nValidating final numeric indicators..."
)


numeric_columns = [

    "decision_score",
    "global_rank",
    "ward_rank",

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
    "population_weighted_environmental_burden",

    "estimated_heat_reduction_C",
    "estimated_emission_reduction"
]


check_numeric(
    final_df,
    numeric_columns
)


print(
    "Numeric validation: PASSED"
)


# ============================================================
# CREATE FINAL DECISION INDICATORS
# ============================================================

print(
    "\nCreating final decision indicators..."
)


final_df["baseline_AQI"] = (
    final_df["final_AQI"]
)


final_df["expected_heat_reduction_C"] = (
    final_df[
        "estimated_heat_reduction_C"
    ]
)


final_df["expected_emission_reduction"] = (
    final_df[
        "estimated_emission_reduction"
    ]
)


final_df["population"] = (
    final_df["TOT_P"]
)


final_df["child_population_percent"] = (
    final_df["children_percent"]
)


# ============================================================
# DECISION PRIORITY
# ============================================================

def classify_priority(score):

    if score >= 0.60:

        return "High Priority"

    elif score >= 0.40:

        return "Medium Priority"

    else:

        return "Lower Priority"


final_df[
    "decision_priority_category"
] = (
    final_df[
        "decision_score"
    ].apply(
        classify_priority
    )
)


# ============================================================
# FINAL STATUS
# ============================================================

final_df[
    "final_decision_status"
] = "Recommended"


# ============================================================
# FINAL COLUMN ORDER
# ============================================================

final_columns = [

    "Ward_No",
    "Ward_Name",

    "intervention",

    "decision_score",
    "global_rank",
    "ward_rank",

    "decision_label",

    "decision_priority_category",
    "final_decision_status",

    "baseline_AQI",

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

    "population",
    "child_population_percent",

    "health_exposure_score",
    "population_vulnerability_index",
    "population_weighted_environmental_burden",

    "expected_heat_reduction_C",
    "expected_emission_reduction",

    "decision_reason",
    "expected_impact_summary",
    "decision_explanation"
]


final_df = final_df[
    final_columns
].copy()


# ============================================================
# MISSING VALUE VALIDATION
# ============================================================

print(
    "\nChecking missing values..."
)


missing_values = (
    final_df.isna().sum()
)

missing_values = (
    missing_values[
        missing_values > 0
    ]
)


if len(missing_values) > 0:

    print(
        missing_values
    )

    raise ValueError(
        "Missing values found in "
        "final decision layer."
    )


print(
    "Missing-value validation: PASSED"
)


# ============================================================
# INFINITE VALUE VALIDATION
# ============================================================

print(
    "\nChecking infinite values..."
)


for column in numeric_columns:

    if column not in final_df.columns:

        continue

    infinite_count = np.isinf(
        final_df[
            column
        ].to_numpy(
            dtype=float
        )
    ).sum()

    print(
        f"{column}: {infinite_count}"
    )

    if infinite_count > 0:

        raise ValueError(
            f"Infinite values found in {column}"
        )


print(
    "Infinite-value validation: PASSED"
)


# ============================================================
# LOAD WARD GEOMETRY
# ============================================================

print(
    "\nLoading ward geometry..."
)


wards = gpd.read_file(
    GEOMETRY_FILE
)


print(
    f"Ward geometry records: "
    f"{len(wards)}"
)


print(
    f"Ward CRS: {wards.crs}"
)


# ============================================================
# PREPARE GEOMETRY
# ============================================================

if "Ward_No" not in wards.columns:

    raise ValueError(
        "Ward_No column missing from "
        "ward geometry."
    )


wards["Ward_No"] = pd.to_numeric(
    wards["Ward_No"],
    errors="coerce"
)


before_count = len(wards)


wards = wards[
    wards["Ward_No"].notna()
].copy()


removed_count = (
    before_count - len(wards)
)


if removed_count > 0:

    print(
        f"Non-numeric geometry records removed: "
        f"{removed_count}"
    )


wards["Ward_No"] = (
    wards["Ward_No"].astype(int)
)


# Keep only standard 272 wards

wards = wards[
    wards["Ward_No"].between(
        1,
        272
    )
].copy()


print(
    f"Numeric ward geometry records: "
    f"{len(wards)}"
)


check_duplicates(
    wards,
    "Ward geometry"
)


# ============================================================
# GEOMETRY COVERAGE
# ============================================================

geometry_wards = set(
    wards["Ward_No"]
)

final_wards = set(
    final_df["Ward_No"]
)


missing_geometry_wards = (
    final_wards - geometry_wards
)


if len(missing_geometry_wards) > 0:

    raise ValueError(
        "Some final wards do not have "
        "geometry."
    )


print(
    "Geometry coverage: PASSED"
)


# ============================================================
# ATTACH GEOMETRY
# ============================================================

print(
    "\nAttaching ward geometry..."
)


geometry_columns = [
    "Ward_No",
    "geometry"
]


final_gdf = wards[
    geometry_columns
].merge(

    final_df,

    on="Ward_No",

    how="inner",

    validate="one_to_one"
)


print(
    f"Final spatial records: "
    f"{len(final_gdf)}"
)


if len(final_gdf) != 272:

    raise ValueError(
        "Final spatial layer does not "
        "contain 272 wards."
    )


# ============================================================
# GEOMETRY VALIDATION
# ============================================================

print(
    "\nValidating geometry..."
)


missing_geometry = (
    final_gdf.geometry.isna().sum()
)

invalid_geometry = (
    (~final_gdf.geometry.is_valid).sum()
)


print(
    f"Missing geometry: "
    f"{missing_geometry}"
)

print(
    f"Invalid geometry: "
    f"{invalid_geometry}"
)


if missing_geometry > 0:

    raise ValueError(
        "Missing geometry found."
    )


if invalid_geometry > 0:

    raise ValueError(
        "Invalid geometry found."
    )


print(
    "Geometry validation: PASSED"
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE CSV
# ============================================================

print(
    "\nSaving final decision CSV..."
)


final_df.to_csv(
    OUTPUT_CSV,
    index=False
)


print(
    f"CSV saved:\n{OUTPUT_CSV}"
)


# ============================================================
# SAVE GEOJSON
# ============================================================

print(
    "\nSaving final decision GeoJSON..."
)


final_gdf.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)


print(
    f"GeoJSON saved:\n{OUTPUT_GEOJSON}"
)


# ============================================================
# CREATE SUMMARY
# ============================================================

summary = {

    "total_wards":
        int(
            final_df[
                "Ward_No"
            ].nunique()
        ),

    "recommended_decisions":
        int(
            len(final_df)
        ),

    "unique_interventions":
        int(
            final_df[
                "intervention"
            ].nunique()
        ),

    "mean_decision_score":
        float(
            final_df[
                "decision_score"
            ].mean()
        ),

    "mean_AQI":
        float(
            final_df[
                "baseline_AQI"
            ].mean()
        ),

    "mean_environmental_risk":
        float(
            final_df[
                "environmental_risk_score"
            ].mean()
        ),

    "mean_health_exposure":
        float(
            final_df[
                "health_exposure_score"
            ].mean()
        ),

    "mean_expected_heat_reduction_C":
        float(
            final_df[
                "expected_heat_reduction_C"
            ].mean()
        ),

    "mean_expected_emission_reduction":
        float(
            final_df[
                "expected_emission_reduction"
            ].mean()
        ),

    "total_population":
        int(
            final_df[
                "population"
            ].sum()
        ),

    "intervention_distribution":
        final_df[
            "intervention"
        ].value_counts().to_dict(),

    "priority_distribution":
        final_df[
            "decision_priority_category"
        ].value_counts().to_dict()
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
# FINAL VALIDATION
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "FINAL DECISION LAYER VALIDATION"
)

print(
    "=" * 70
)


print(
    f"272 wards: "
    f"{final_df['Ward_No'].nunique() == 272}"
)


print(
    f"Recommended decisions: "
    f"{len(final_df) == 272}"
)


print(
    f"Decision scores available: "
    f"{final_df['decision_score'].notna().all()}"
)


print(
    f"Environmental risk available: "
    f"{final_df['environmental_risk_score'].notna().all()}"
)


print(
    f"Health exposure available: "
    f"{final_df['health_exposure_score'].notna().all()}"
)


print(
    f"Interventions available: "
    f"{final_df['intervention'].notna().all()}"
)


print(
    f"Explanations available: "
    f"{final_df['decision_explanation'].notna().all()}"
)


print(
    f"Geometry available: "
    f"{final_gdf.geometry.notna().all()}"
)


print(
    f"Geometry valid: "
    f"{final_gdf.geometry.is_valid.all()}"
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


# ============================================================
# SUMMARY
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "FINAL WARD DECISION SUMMARY"
)

print(
    "=" * 70
)


print(
    f"Total wards: "
    f"{final_df['Ward_No'].nunique()}"
)


print(
    f"Mean decision score: "
    f"{final_df['decision_score'].mean():.4f}"
)


print(
    f"Mean AQI: "
    f"{final_df['baseline_AQI'].mean():.2f}"
)


print(
    f"Mean environmental risk: "
    f"{final_df['environmental_risk_score'].mean():.3f}"
)


print(
    f"Mean health exposure: "
    f"{final_df['health_exposure_score'].mean():.2f}"
)


print(
    f"Mean expected heat reduction: "
    f"{final_df['expected_heat_reduction_C'].mean():.2f} °C"
)


print(
    f"Mean expected emission reduction: "
    f"{final_df['expected_emission_reduction'].mean():.3f}"
)


print(
    "\nIntervention distribution:"
)

print(
    final_df[
        "intervention"
    ].value_counts()
)


print(
    "\nDecision priority distribution:"
)

print(
    final_df[
        "decision_priority_category"
    ].value_counts()
)


print(
    "\nOutput files:"
)

print(
    OUTPUT_CSV
)

print(
    OUTPUT_GEOJSON
)

print(
    OUTPUT_SUMMARY
)


print(
    "\n" + "=" * 70
)

print(
    "FINAL WARD DECISION LAYER "
    "CREATED SUCCESSFULLY"
)

print(
    "=" * 70
)