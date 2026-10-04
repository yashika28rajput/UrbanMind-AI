import os
import json
import numpy as np
import pandas as pd


# ============================================================
# UrbanMind AI - AQI ML Dataset Preparation
# ============================================================

INPUT_FILE = "data/raw/air_quality/delhi_air_quality_measurements_july_2026.csv"

OUTPUT_DIR = "data/processed/ml/aqi"

FULL_DATASET = os.path.join(OUTPUT_DIR, "delhi_aqi_ml_dataset.csv")
TRAIN_DATASET = os.path.join(OUTPUT_DIR, "delhi_aqi_train.csv")
VALIDATION_DATASET = os.path.join(OUTPUT_DIR, "delhi_aqi_validation.csv")
TEST_DATASET = os.path.join(OUTPUT_DIR, "delhi_aqi_test.csv")
SUMMARY_FILE = os.path.join(OUTPUT_DIR, "aqi_dataset_summary.json")


print("=" * 70)
print("UrbanMind AI - AQI ML Dataset Preparation")
print("=" * 70)


# ============================================================
# 1. CHECK INPUT
# ============================================================

print("\nChecking raw AQI dataset...")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(f"AQI dataset not found: {INPUT_FILE}")

print("Raw AQI dataset: FOUND")


# ============================================================
# 2. LOAD DATA
# ============================================================

print("\nLoading AQI measurements...")

df = pd.read_csv(INPUT_FILE)

print(f"Rows: {len(df)}")
print(f"Columns: {df.columns.tolist()}")


required_columns = [
    "location_id",
    "station_name",
    "sensor_id",
    "parameter",
    "value",
    "units",
    "timestamp_local",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

print("Required columns: PASSED")


# ============================================================
# 3. BASIC CLEANING
# ============================================================

print("\nCleaning raw measurements...")

df["value"] = pd.to_numeric(
    df["value"],
    errors="coerce"
)

df["timestamp_local"] = pd.to_datetime(
    df["timestamp_local"],
    errors="coerce"
)

before = len(df)

df = df.dropna(
    subset=[
        "location_id",
        "station_name",
        "parameter",
        "timestamp_local",
        "value",
    ]
).copy()

removed = before - len(df)

print(f"Rows removed during cleaning: {removed}")
print(f"Rows after cleaning: {len(df)}")


# ============================================================
# 4. KEEP REQUIRED POLLUTANTS
# ============================================================

print("\nFiltering pollutant parameters...")

pollutants = [
    "pm25",
    "pm10",
    "no2",
    "o3",
    "co",
    "so2",
]

df = df[
    df["parameter"].isin(pollutants)
].copy()

print("Pollutants used:")

for pollutant in pollutants:
    count = (df["parameter"] == pollutant).sum()
    print(f"{pollutant}: {count}")


# ============================================================
# 5. CREATE TIME FEATURES
# ============================================================

print("\nCreating temporal features...")

df["date"] = df["timestamp_local"].dt.date

df["hour"] = df["timestamp_local"].dt.hour

df["day"] = df["timestamp_local"].dt.day

df["day_of_week"] = df[
    "timestamp_local"
].dt.dayofweek

df["month"] = df[
    "timestamp_local"
].dt.month


# ============================================================
# 6. PIVOT POLLUTANTS
# ============================================================

print("\nPivoting pollutant measurements...")

pivot = df.pivot_table(
    index=[
        "location_id",
        "station_name",
        "timestamp_local",
        "date",
        "hour",
        "day",
        "day_of_week",
        "month",
    ],
    columns="parameter",
    values="value",
    aggfunc="mean",
).reset_index()


pivot.columns.name = None


# Ensure all pollutant columns exist

for pollutant in pollutants:
    if pollutant not in pivot.columns:
        pivot[pollutant] = np.nan


print(f"Pivoted records: {len(pivot)}")


# ============================================================
# 7. SORT DATA
# ============================================================

pivot = pivot.sort_values(
    [
        "station_name",
        "timestamp_local",
    ]
).reset_index(drop=True)


# ============================================================
# 8. HANDLE MISSING POLLUTANTS
# ============================================================

print("\nHandling missing pollutant values...")

for pollutant in pollutants:

    missing_before = pivot[pollutant].isna().sum()

    pivot[pollutant] = (
        pivot
        .groupby("station_name")[pollutant]
        .transform(
            lambda x: x.interpolate(
                method="linear",
                limit_direction="both"
            )
        )
    )

    missing_after = pivot[pollutant].isna().sum()

    print(
        f"{pollutant}: "
        f"{missing_before} missing -> "
        f"{missing_after} missing"
    )


# ============================================================
# 9. DROP ROWS WHERE POLLUTANT DATA IS STILL UNAVAILABLE
# ============================================================

pivot = pivot.dropna(
    subset=pollutants,
    how="all"
).copy()


# ============================================================
# 10. CALCULATE POLLUTANT SUB-INDICES
# ============================================================

print("\nCalculating pollutant sub-indices...")

# NOTE:
# These are simplified modelling indices.
# They are NOT being presented as official CPCB AQI calculations.

def normalize_index(series, low, high):

    result = (
        (series - low)
        / (high - low)
    ) * 100

    return result.clip(0, 500)


pivot["pm25_index"] = normalize_index(
    pivot["pm25"],
    0,
    250
)

pivot["pm10_index"] = normalize_index(
    pivot["pm10"],
    0,
    430
)

pivot["no2_index"] = normalize_index(
    pivot["no2"],
    0,
    400
)

pivot["o3_index"] = normalize_index(
    pivot["o3"],
    0,
    400
)

pivot["so2_index"] = normalize_index(
    pivot["so2"],
    0,
    400
)

pivot["co_index"] = normalize_index(
    pivot["co"],
    0,
    50
)


# ============================================================
# 11. CALCULATE MODELLING AQI TARGET
# ============================================================

print("\nCreating AQI target...")

index_columns = [
    "pm25_index",
    "pm10_index",
    "no2_index",
    "o3_index",
    "so2_index",
    "co_index",
]

pivot["AQI"] = pivot[index_columns].max(
    axis=1,
    skipna=True
)

pivot["AQI"] = pivot["AQI"].clip(
    lower=0,
    upper=500
)


# ============================================================
# 12. AQI CATEGORY
# ============================================================

def aqi_category(aqi):

    if aqi <= 50:
        return "Good"

    elif aqi <= 100:
        return "Satisfactory"

    elif aqi <= 200:
        return "Moderate"

    elif aqi <= 300:
        return "Poor"

    elif aqi <= 400:
        return "Very Poor"

    else:
        return "Severe"


pivot["AQI_category"] = pivot[
    "AQI"
].apply(aqi_category)


# ============================================================
# 13. CREATE LAG FEATURES
# ============================================================

print("\nCreating temporal lag features...")

group = pivot.groupby(
    "station_name",
    group_keys=False
)

pivot["pm25_lag_1"] = group["pm25"].shift(1)
pivot["pm10_lag_1"] = group["pm10"].shift(1)
pivot["no2_lag_1"] = group["no2"].shift(1)
pivot["o3_lag_1"] = group["o3"].shift(1)

pivot["AQI_lag_1"] = group["AQI"].shift(1)


# ============================================================
# 14. REMOVE FIRST LAGGED ROWS
# ============================================================

pivot = pivot.dropna(
    subset=["AQI_lag_1"]
).copy()


# ============================================================
# 15. FINAL FEATURE LIST
# ============================================================

feature_columns = [
    "pm25",
    "pm10",
    "no2",
    "o3",
    "co",
    "so2",

    "pm25_index",
    "pm10_index",
    "no2_index",
    "o3_index",
    "so2_index",
    "co_index",

    "pm25_lag_1",
    "pm10_lag_1",
    "no2_lag_1",
    "o3_lag_1",
    "AQI_lag_1",

    "hour",
    "day",
    "day_of_week",
    "month",
]


# ============================================================
# 16. NUMERIC CONVERSION
# ============================================================

print("\nConverting features to numeric...")

for column in feature_columns:

    pivot[column] = pd.to_numeric(
        pivot[column],
        errors="coerce"
    )


pivot["AQI"] = pd.to_numeric(
    pivot["AQI"],
    errors="coerce"
)


# ============================================================
# 17. REMOVE INVALID ROWS
# ============================================================

pivot = pivot.dropna(
    subset=feature_columns + ["AQI"]
).copy()


# ============================================================
# 18. INFINITE VALUE CHECK
# ============================================================

pivot = pivot.replace(
    [np.inf, -np.inf],
    np.nan
)

pivot = pivot.dropna(
    subset=feature_columns + ["AQI"]
).copy()


# ============================================================
# 19. FINAL DATASET
# ============================================================

final_columns = [
    "location_id",
    "station_name",
    "timestamp_local",
] + feature_columns + [
    "AQI",
    "AQI_category",
]

ml_dataset = pivot[
    final_columns
].copy()


# ============================================================
# 20. SORT BY TIME
# ============================================================

ml_dataset = ml_dataset.sort_values(
    "timestamp_local"
).reset_index(drop=True)


# ============================================================
# 21. TIME-BASED TRAIN / VALIDATION / TEST SPLIT
# ============================================================

print("\nCreating time-based train/validation/test split...")

total = len(ml_dataset)

train_end = int(total * 0.70)

validation_end = int(total * 0.85)

train = ml_dataset.iloc[
    :train_end
].copy()

validation = ml_dataset.iloc[
    train_end:validation_end
].copy()

test = ml_dataset.iloc[
    validation_end:
].copy()


# ============================================================
# 22. VALIDATION
# ============================================================

print("\nValidating final ML dataset...")

print(f"Total records: {len(ml_dataset)}")
print(f"Training records: {len(train)}")
print(f"Validation records: {len(validation)}")
print(f"Testing records: {len(test)}")

print(
    "Missing values:",
    ml_dataset.isna().sum().sum()
)

numeric_columns = feature_columns + ["AQI"]

infinite_count = np.isinf(
    ml_dataset[numeric_columns]
).sum().sum()

print(
    "Infinite values:",
    infinite_count
)

print(
    "AQI minimum:",
    round(ml_dataset["AQI"].min(), 2)
)

print(
    "AQI maximum:",
    round(ml_dataset["AQI"].max(), 2)
)

print(
    "AQI mean:",
    round(ml_dataset["AQI"].mean(), 2)
)


# ============================================================
# 23. CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# 24. SAVE DATASETS
# ============================================================

print("\nSaving AQI ML datasets...")

ml_dataset.to_csv(
    FULL_DATASET,
    index=False
)

train.to_csv(
    TRAIN_DATASET,
    index=False
)

validation.to_csv(
    VALIDATION_DATASET,
    index=False
)

test.to_csv(
    TEST_DATASET,
    index=False
)


# ============================================================
# 25. SUMMARY
# ============================================================

summary = {
    "total_records": int(len(ml_dataset)),
    "training_records": int(len(train)),
    "validation_records": int(len(validation)),
    "testing_records": int(len(test)),
    "stations": int(
        ml_dataset["station_name"].nunique()
    ),
    "features": feature_columns,
    "target": "AQI",
    "aqi_min": float(
        ml_dataset["AQI"].min()
    ),
    "aqi_max": float(
        ml_dataset["AQI"].max()
    ),
    "aqi_mean": float(
        ml_dataset["AQI"].mean()
    ),
}


with open(
    SUMMARY_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=4
    )


# ============================================================
# 26. FINAL OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("AQI ML DATASET PREPARATION SUMMARY")
print("=" * 70)

print(
    f"Total records      : {len(ml_dataset)}"
)

print(
    f"Stations            : "
    f"{ml_dataset['station_name'].nunique()}"
)

print(
    f"Features            : "
    f"{len(feature_columns)}"
)

print(
    f"Target              : AQI"
)

print(
    f"Train               : {len(train)}"
)

print(
    f"Validation          : {len(validation)}"
)

print(
    f"Test                : {len(test)}"
)

print(
    f"AQI minimum         : "
    f"{ml_dataset['AQI'].min():.2f}"
)

print(
    f"AQI maximum         : "
    f"{ml_dataset['AQI'].max():.2f}"
)

print(
    f"AQI mean            : "
    f"{ml_dataset['AQI'].mean():.2f}"
)

print("\nOutput files:")

print(FULL_DATASET)
print(TRAIN_DATASET)
print(VALIDATION_DATASET)
print(TEST_DATASET)
print(SUMMARY_FILE)

print("\nAQI ML DATASET PREPARATION COMPLETED SUCCESSFULLY")
print("=" * 70)