import os
import numpy as np
import pandas as pd
import geopandas as gpd


print("=" * 60)
print("UrbanMind AI - Heat Risk Spatial Layer")
print("=" * 60)


# ============================================================
# PATHS
# ============================================================

PREDICTION_PATH = (
    "data/processed/ml/"
    "urban_heat_predictions.csv"
)

UNIFIED_GEOJSON = (
    "data/processed/urban/"
    "delhi_unified_urban_dataset.geojson"
)

OUTPUT_DIR = (
    "data/processed/ml/"
)

OUTPUT_GEOJSON = (
    OUTPUT_DIR +
    "delhi_ward_heat_risk.geojson"
)

OUTPUT_CSV = (
    OUTPUT_DIR +
    "delhi_ward_heat_risk.csv"
)


# ============================================================
# CHECK INPUT FILES
# ============================================================

print("\nChecking required files...")

if not os.path.exists(PREDICTION_PATH):

    raise FileNotFoundError(
        f"Prediction file not found:\n"
        f"{PREDICTION_PATH}"
    )

print("Heat predictions: FOUND")


if not os.path.exists(UNIFIED_GEOJSON):

    raise FileNotFoundError(
        f"Unified urban GeoJSON not found:\n"
        f"{UNIFIED_GEOJSON}"
    )

print("Unified ward geometry: FOUND")


# ============================================================
# LOAD PREDICTIONS
# ============================================================

print("\nLoading heat predictions...")

predictions = pd.read_csv(
    PREDICTION_PATH
)

print(
    f"Prediction records: "
    f"{len(predictions)}"
)

print(
    "Prediction columns:"
)

print(
    predictions.columns.tolist()
)


# ============================================================
# LOAD WARD GEOMETRIES
# ============================================================

print("\nLoading ward geometries...")

wards = gpd.read_file(
    UNIFIED_GEOJSON
)

print(
    f"Ward geometry records: "
    f"{len(wards)}"
)

print(
    f"CRS: {wards.crs}"
)


# ============================================================
# VALIDATE WARD COLUMNS
# ============================================================

print("\nValidating Ward_No columns...")

if "Ward_No" not in predictions.columns:

    raise ValueError(
        "Ward_No missing from prediction dataset."
    )


if "Ward_No" not in wards.columns:

    raise ValueError(
        "Ward_No missing from ward geometry dataset."
    )


# ============================================================
# NORMALIZE WARD IDs
# ============================================================

print("\nNormalizing Ward IDs...")

predictions["Ward_No"] = pd.to_numeric(
    predictions["Ward_No"],
    errors="coerce"
)

wards["Ward_No"] = pd.to_numeric(
    wards["Ward_No"],
    errors="coerce"
)


if predictions["Ward_No"].isna().any():

    raise ValueError(
        "Invalid Ward_No values found "
        "in predictions."
    )


if wards["Ward_No"].isna().any():

    raise ValueError(
        "Invalid Ward_No values found "
        "in ward geometries."
    )


predictions["Ward_No"] = (
    predictions["Ward_No"]
    .astype("int64")
)

wards["Ward_No"] = (
    wards["Ward_No"]
    .astype("int64")
)


print(
    "Ward IDs normalized to int64"
)


# ============================================================
# CHECK DUPLICATES
# ============================================================

prediction_duplicates = (
    predictions["Ward_No"]
    .duplicated()
    .sum()
)

ward_duplicates = (
    wards["Ward_No"]
    .duplicated()
    .sum()
)


print(
    f"Prediction duplicate wards: "
    f"{prediction_duplicates}"
)

print(
    f"Geometry duplicate wards: "
    f"{ward_duplicates}"
)


if prediction_duplicates != 0:

    raise ValueError(
        "Duplicate wards found "
        "in prediction dataset."
    )


if ward_duplicates != 0:

    raise ValueError(
        "Duplicate wards found "
        "in geometry dataset."
    )


# ============================================================
# CHECK WARD COVERAGE
# ============================================================

print("\nChecking ward coverage...")

prediction_wards = set(
    predictions["Ward_No"]
)

geometry_wards = set(
    wards["Ward_No"]
)


prediction_only = (
    prediction_wards -
    geometry_wards
)

geometry_only = (
    geometry_wards -
    prediction_wards
)


print(
    f"Prediction-only wards: "
    f"{len(prediction_only)}"
)

print(
    f"Geometry-only wards: "
    f"{len(geometry_only)}"
)


if prediction_only:

    raise ValueError(
        "Prediction dataset contains "
        "wards missing from geometry."
    )


if geometry_only:

    raise ValueError(
        "Geometry dataset contains "
        "wards missing from predictions."
    )


print(
    "Ward coverage validation: PASSED"
)


# ============================================================
# SELECT PREDICTION FEATURES
# ============================================================

print(
    "\nPreparing heat prediction features..."
)


required_prediction_columns = [
    "Ward_No",
    "Ward_Name",
    "mean_LST_C",
    "predicted_LST_C",
    "prediction_error_C",
    "absolute_error_C",
    "heat_risk_category",
    "heat_anomaly_C"
]


missing_columns = [
    column
    for column in required_prediction_columns
    if column not in predictions.columns
]


if missing_columns:

    raise ValueError(
        "Missing prediction columns:\n"
        f"{missing_columns}"
    )


prediction_features = predictions[
    required_prediction_columns
].copy()


# ============================================================
# MERGE WITH GEOMETRY
# ============================================================

print(
    "\nMerging heat predictions "
    "with ward geometry..."
)


heat_risk = wards.merge(
    prediction_features,
    on="Ward_No",
    how="left",
    suffixes=(
        "",
        "_prediction"
    )
)


print(
    f"Merged records: "
    f"{len(heat_risk)}"
)


# ============================================================
# HANDLE DUPLICATE WARD NAME
# ============================================================

if (
    "Ward_Name_prediction"
    in heat_risk.columns
):

    heat_risk["Ward_Name"] = (
        heat_risk["Ward_Name_prediction"]
        .fillna(
            heat_risk["Ward_Name"]
        )
    )

    heat_risk = heat_risk.drop(
        columns=[
            "Ward_Name_prediction"
        ]
    )


# ============================================================
# VALIDATE MERGE
# ============================================================

print(
    "\nValidating merged heat-risk layer..."
)


print(
    f"Records: {len(heat_risk)}"
)

print(
    f"Unique wards: "
    f"{heat_risk['Ward_No'].nunique()}"
)


duplicate_after_merge = (
    heat_risk["Ward_No"]
    .duplicated()
    .sum()
)


missing_predictions = (
    heat_risk[
        "predicted_LST_C"
    ]
    .isna()
    .sum()
)


missing_risk = (
    heat_risk[
        "heat_risk_category"
    ]
    .isna()
    .sum()
)


missing_geometry = (
    heat_risk.geometry
    .isna()
    .sum()
)


invalid_geometry = (
    (~heat_risk.geometry.is_valid)
    .sum()
)


print(
    f"Duplicate wards: "
    f"{duplicate_after_merge}"
)

print(
    f"Missing predictions: "
    f"{missing_predictions}"
)

print(
    f"Missing heat-risk category: "
    f"{missing_risk}"
)

print(
    f"Missing geometry: "
    f"{missing_geometry}"
)

print(
    f"Invalid geometry: "
    f"{invalid_geometry}"
)


if len(heat_risk) != 272:

    raise ValueError(
        f"Expected 272 wards, "
        f"found {len(heat_risk)}"
    )


if (
    heat_risk["Ward_No"].nunique()
    != 272
):

    raise ValueError(
        "Ward uniqueness validation failed."
    )


if duplicate_after_merge != 0:

    raise ValueError(
        "Duplicate wards after merge."
    )


if missing_predictions != 0:

    raise ValueError(
        "Some wards have no predicted LST."
    )


if missing_risk != 0:

    raise ValueError(
        "Some wards have no heat-risk category."
    )


if missing_geometry != 0:

    raise ValueError(
        "Some wards have missing geometry."
    )


if invalid_geometry != 0:

    raise ValueError(
        "Some ward geometries are invalid."
    )


# ============================================================
# NUMERIC VALIDATION
# ============================================================

print(
    "\nValidating heat prediction values..."
)


numeric_columns = [
    "mean_LST_C",
    "predicted_LST_C",
    "prediction_error_C",
    "absolute_error_C",
    "heat_anomaly_C"
]


for column in numeric_columns:

    heat_risk[column] = pd.to_numeric(
        heat_risk[column],
        errors="coerce"
    )


missing_numeric = (
    heat_risk[numeric_columns]
    .isna()
    .sum()
    .sum()
)


if missing_numeric > 0:

    raise ValueError(
        f"Missing numeric values: "
        f"{missing_numeric}"
    )


infinite_numeric = np.isinf(
    heat_risk[
        numeric_columns
    ]
    .to_numpy()
).sum()


if infinite_numeric > 0:

    raise ValueError(
        f"Infinite numeric values: "
        f"{infinite_numeric}"
    )


print(
    "Numeric validation: PASSED"
)


# ============================================================
# HEAT RISK DISTRIBUTION
# ============================================================

print(
    "\nHeat-risk distribution:"
)


risk_counts = (
    heat_risk[
        "heat_risk_category"
    ]
    .value_counts()
)


for category, count in (
    risk_counts.items()
):

    percentage = (
        count /
        len(heat_risk)
    ) * 100

    print(
        f"{category}: "
        f"{count} wards "
        f"({percentage:.2f}%)"
    )


# ============================================================
# SORT BY PREDICTED LST
# ============================================================

heat_risk = heat_risk.sort_values(
    "predicted_LST_C",
    ascending=False
).reset_index(
    drop=True
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE GEOJSON
# ============================================================

print(
    "\nSaving heat-risk GeoJSON..."
)


heat_risk.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)


print(
    f"GeoJSON saved:\n"
    f"{OUTPUT_GEOJSON}"
)


# ============================================================
# SAVE CSV
# ============================================================

print(
    "\nSaving heat-risk CSV..."
)


csv_data = heat_risk.drop(
    columns="geometry"
).copy()


csv_data.to_csv(
    OUTPUT_CSV,
    index=False
)


print(
    f"CSV saved:\n"
    f"{OUTPUT_CSV}"
)


# ============================================================
# TOP HOT WARDS
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "TOP 10 PREDICTED HOT WARDS"
)

print(
    "=" * 60
)


display_columns = [
    "Ward_No",
    "Ward_Name",
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C",
    "heat_risk_category"
]


print(
    heat_risk[
        display_columns
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# FINAL VALIDATION
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "FINAL HEAT RISK LAYER VALIDATION"
)

print(
    "=" * 60
)


final_checks = {

    "272 wards":
        len(heat_risk) == 272,

    "Unique Ward_No":
        heat_risk[
            "Ward_No"
        ].nunique() == 272,

    "Predictions available":
        heat_risk[
            "predicted_LST_C"
        ].notna().all(),

    "Risk categories available":
        heat_risk[
            "heat_risk_category"
        ].notna().all(),

    "No missing geometry":
        heat_risk.geometry
        .notna()
        .all(),

    "No invalid geometry":
        heat_risk.geometry
        .is_valid
        .all(),

    "No infinite predictions":
        np.isinf(
            heat_risk[
                "predicted_LST_C"
            ]
            .to_numpy()
        ).sum() == 0,

    "GeoJSON exists":
        os.path.exists(
            OUTPUT_GEOJSON
        ),

    "CSV exists":
        os.path.exists(
            OUTPUT_CSV
        )
}


for name, status in (
    final_checks.items()
):

    print(
        f"{name}: {status}"
    )


if not all(
    final_checks.values()
):

    raise ValueError(
        "Heat-risk layer validation failed."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "HEAT RISK SPATIAL LAYER SUMMARY"
)

print(
    "=" * 60
)

print(
    f"Wards: {len(heat_risk)}"
)

print(
    f"CRS: {heat_risk.crs}"
)

print(
    "Actual LST range: "
    f"{heat_risk['mean_LST_C'].min():.2f} - "
    f"{heat_risk['mean_LST_C'].max():.2f} °C"
)

print(
    "Predicted LST range: "
    f"{heat_risk['predicted_LST_C'].min():.2f} - "
    f"{heat_risk['predicted_LST_C'].max():.2f} °C"
)

print(
    "\nOutput files:"
)

print(
    OUTPUT_GEOJSON
)

print(
    OUTPUT_CSV
)


print(
    "\n" + "=" * 60
)

print(
    "HEAT RISK SPATIAL LAYER "
    "CREATED SUCCESSFULLY"
)

print(
    "=" * 60
)