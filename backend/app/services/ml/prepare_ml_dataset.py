import os
import numpy as np
import pandas as pd


print("=" * 60)
print("UrbanMind AI - ML Dataset Preparation")
print("=" * 60)


# ============================================================
# Paths
# ============================================================

INPUT_PATH = (
    "data/processed/urban/"
    "delhi_unified_urban_dataset.csv"
)

OUTPUT_DIR = "data/processed/ml"

OUTPUT_ALL = (
    f"{OUTPUT_DIR}/"
    "urban_heat_ml_dataset.csv"
)

OUTPUT_TRAIN = (
    f"{OUTPUT_DIR}/"
    "urban_heat_train.csv"
)

OUTPUT_VALIDATION = (
    f"{OUTPUT_DIR}/"
    "urban_heat_validation.csv"
)

OUTPUT_TEST = (
    f"{OUTPUT_DIR}/"
    "urban_heat_test.csv"
)


# ============================================================
# Configuration
# ============================================================

TARGET = "mean_LST_C"

RANDOM_STATE = 42


# ============================================================
# Check Input
# ============================================================

print("\nChecking unified dataset...")

if not os.path.exists(INPUT_PATH):

    raise FileNotFoundError(
        f"Unified dataset not found:\n{INPUT_PATH}"
    )

print("Unified dataset: FOUND")


# ============================================================
# Load Dataset
# ============================================================

print("\nLoading unified dataset...")

df = pd.read_csv(INPUT_PATH)

print(
    f"Rows: {len(df)}"
)

print(
    f"Columns: {len(df.columns)}"
)


# ============================================================
# Basic Validation
# ============================================================

print("\nRunning basic validation...")

if TARGET not in df.columns:

    raise ValueError(
        f"Target column '{TARGET}' "
        "not found."
    )


if df["Ward_No"].duplicated().any():

    raise ValueError(
        "Duplicate Ward_No values found."
    )


if df[TARGET].isna().any():

    raise ValueError(
        "Missing target values found."
    )


if np.isinf(
    df[TARGET].to_numpy()
).any():

    raise ValueError(
        "Infinite target values found."
    )


print("Basic validation: PASSED")


# ============================================================
# Define Identifier Columns
# ============================================================

ID_COLUMNS = [
    "Ward_No",
    "Ward_Name"
]


# ============================================================
# Define Features
# ============================================================

FEATURE_COLUMNS = [

    # ------------------------------
    # Population / Demographics
    # ------------------------------

    "TOT_P",
    "No_HH",
    "TOT_M",
    "TOT_F",
    "P_06",
    "P_LIT",
    "P_ILL",

    # ------------------------------
    # Land Use / Land Cover
    # ------------------------------

    "water",
    "trees",
    "grass",
    "flooded_vegetation",
    "crops",
    "shrub_and_scrub",
    "built",
    "bare",
    "snow_and_ice",

    "vegetation",
    "built_environment",
    "water_surface",

    # ------------------------------
    # Road / Mobility
    # ------------------------------

    "road_segment_count",
    "oneway_road_segments",

    "total_road_length_km",
    "primary_road_length_km",
    "secondary_road_length_km",
    "tertiary_road_length_km",
    "residential_road_length_km",
    "major_road_length_km",

    "average_road_segment_length_m",
    "oneway_fraction",

    # ------------------------------
    # Spatial Road Density
    # ------------------------------

    "road_density_km_per_km2",
    "major_road_density_km_per_km2",

    # ------------------------------
    # Environmental Pressure
    # ------------------------------

    "traffic_pressure_index",
    "built_pressure_index",
    "heat_pressure_index",

    "vegetation_mitigation_index",
    "emission_pressure_index",

    # ------------------------------
    # Policy / Intervention
    # ------------------------------

    "green_cover_intervention_potential",
    "urban_forest_potential",
    "roadside_greening_potential",

    "cool_roof_intervention_potential",
    "water_body_restoration_potential",

    "heat_mitigation_potential",
    "air_pollution_mitigation_potential",

    "sustainable_mobility_potential",
    "urban_intervention_potential"
]


# ============================================================
# Verify Feature Columns
# ============================================================

print(
    "\nChecking feature columns..."
)


missing_features = [
    column
    for column in FEATURE_COLUMNS
    if column not in df.columns
]


if missing_features:

    print(
        "Missing feature columns:"
    )

    for column in missing_features:

        print(
            f"- {column}"
        )

    raise ValueError(
        "Required ML features are missing."
    )


print(
    f"Features available: "
    f"{len(FEATURE_COLUMNS)}"
)

print(
    "Feature validation: PASSED"
)


# ============================================================
# Create ML Dataset
# ============================================================

print(
    "\nCreating ML dataset..."
)


ml_df = df[
    ID_COLUMNS
    + FEATURE_COLUMNS
    + [TARGET]
].copy()


# ============================================================
# Numeric Conversion
# ============================================================

print(
    "Converting features to numeric..."
)


for column in FEATURE_COLUMNS:

    ml_df[column] = pd.to_numeric(
        ml_df[column],
        errors="coerce"
    )


ml_df[TARGET] = pd.to_numeric(
    ml_df[TARGET],
    errors="coerce"
)


# ============================================================
# Missing Value Check
# ============================================================

print(
    "\nChecking missing values..."
)


feature_missing = (
    ml_df[FEATURE_COLUMNS]
    .isna()
    .sum()
)


target_missing = (
    ml_df[TARGET]
    .isna()
    .sum()
)


if feature_missing.sum() > 0:

    print(
        feature_missing[
            feature_missing > 0
        ]
    )

    raise ValueError(
        "Missing feature values found."
    )


if target_missing > 0:

    raise ValueError(
        "Missing target values found."
    )


print(
    "Missing values: 0"
)


# ============================================================
# Infinite Value Check
# ============================================================

print(
    "\nChecking infinite values..."
)


numeric_data = ml_df[
    FEATURE_COLUMNS
    + [TARGET]
]


infinite_count = np.isinf(
    numeric_data.to_numpy()
).sum()


if infinite_count > 0:

    raise ValueError(
        f"Found {infinite_count} "
        "infinite values."
    )


print(
    "Infinite values: 0"
)


# ============================================================
# Feature Statistics
# ============================================================

print(
    "\nFeature statistics:"
)


print(
    f"Number of features: "
    f"{len(FEATURE_COLUMNS)}"
)


print(
    f"Target: {TARGET}"
)


print(
    f"Target minimum: "
    f"{ml_df[TARGET].min():.4f}"
)


print(
    f"Target maximum: "
    f"{ml_df[TARGET].max():.4f}"
)


print(
    f"Target mean: "
    f"{ml_df[TARGET].mean():.4f}"
)


print(
    f"Target median: "
    f"{ml_df[TARGET].median():.4f}"
)


# ============================================================
# Create Output Directory
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# Train / Validation / Test Split
# ============================================================

print(
    "\nCreating train/validation/test split..."
)


# First shuffle the ward-level dataset.

shuffled = ml_df.sample(
    frac=1,
    random_state=RANDOM_STATE
).reset_index(
    drop=True
)


total_rows = len(shuffled)


train_end = int(
    total_rows * 0.70
)

validation_end = int(
    total_rows * 0.85
)


train_df = shuffled[
    :train_end
].copy()


validation_df = shuffled[
    train_end:validation_end
].copy()


test_df = shuffled[
    validation_end:
].copy()


print(
    f"Total records: "
    f"{total_rows}"
)

print(
    f"Training records: "
    f"{len(train_df)}"
)

print(
    f"Validation records: "
    f"{len(validation_df)}"
)

print(
    f"Testing records: "
    f"{len(test_df)}"
)


# ============================================================
# Check Split Coverage
# ============================================================

split_wards = set(
    train_df["Ward_No"]
).union(
    set(validation_df["Ward_No"])
).union(
    set(test_df["Ward_No"])
)


if len(split_wards) != total_rows:

    raise ValueError(
        "Ward overlap or missing wards "
        "detected between splits."
    )


print(
    "Train/validation/test coverage: PASSED"
)


# ============================================================
# Save Full ML Dataset
# ============================================================

print(
    "\nSaving ML dataset..."
)


ml_df.to_csv(
    OUTPUT_ALL,
    index=False
)


print(
    f"Saved:\n{OUTPUT_ALL}"
)


# ============================================================
# Save Training Dataset
# ============================================================

train_df.to_csv(
    OUTPUT_TRAIN,
    index=False
)


print(
    f"Training dataset saved:\n"
    f"{OUTPUT_TRAIN}"
)


# ============================================================
# Save Validation Dataset
# ============================================================

validation_df.to_csv(
    OUTPUT_VALIDATION,
    index=False
)


print(
    f"Validation dataset saved:\n"
    f"{OUTPUT_VALIDATION}"
)


# ============================================================
# Save Test Dataset
# ============================================================

test_df.to_csv(
    OUTPUT_TEST,
    index=False
)


print(
    f"Test dataset saved:\n"
    f"{OUTPUT_TEST}"
)


# ============================================================
# Final Summary
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "ML DATASET PREPARATION SUMMARY"
)

print(
    "=" * 60
)

print(
    f"Total wards: {len(ml_df)}"
)

print(
    f"Features: {len(FEATURE_COLUMNS)}"
)

print(
    f"Target: {TARGET}"
)

print(
    f"Train: {len(train_df)}"
)

print(
    f"Validation: {len(validation_df)}"
)

print(
    f"Test: {len(test_df)}"
)


# ============================================================
# Final Validation
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "FINAL ML DATASET VALIDATION"
)

print(
    "=" * 60
)


checks = {

    "272 records":
        len(ml_df) == 272,

    "45 ML features":
        len(FEATURE_COLUMNS) == 45,

    "Target exists":
        TARGET in ml_df.columns,

    "No missing values":
        ml_df.isna().sum().sum() == 0,

    "No infinite values":
        np.isinf(
            ml_df[
                FEATURE_COLUMNS
                + [TARGET]
            ].to_numpy()
        ).sum() == 0,

    "All wards unique":
        ml_df["Ward_No"].nunique() == 272,

    "All splits covered":
        len(split_wards) == 272
}


for name, result in checks.items():

    print(
        f"{name}: {result}"
    )


if not all(checks.values()):

    raise ValueError(
        "ML dataset validation failed."
    )


print(
    "\nML DATASET PREPARATION "
    "COMPLETED SUCCESSFULLY"
)

print(
    "=" * 60
)