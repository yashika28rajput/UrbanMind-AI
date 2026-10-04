import os
import numpy as np
import pandas as pd
import geopandas as gpd


print("=" * 70)
print("UrbanMind AI - Ward-Level AQI Spatial Layer")
print("=" * 70)


# ============================================================
# PATHS
# ============================================================

AQI_SPATIAL_FILE = (
    "data/processed/ml/aqi/delhi_aqi_spatial_layer.geojson"
)

WARD_FILE = (
    "data/processed/urban/delhi_unified_urban_dataset.geojson"
)

OUTPUT_DIR = "data/processed/ml/aqi"

OUTPUT_GEOJSON = (
    f"{OUTPUT_DIR}/delhi_ward_aqi.geojson"
)

OUTPUT_CSV = (
    f"{OUTPUT_DIR}/delhi_ward_aqi.csv"
)

OUTPUT_SUMMARY = (
    f"{OUTPUT_DIR}/ward_aqi_summary.json"
)


# ============================================================
# CHECK FILES
# ============================================================

print("\nChecking required files...")

if not os.path.exists(AQI_SPATIAL_FILE):
    raise FileNotFoundError(
        f"AQI spatial layer not found: {AQI_SPATIAL_FILE}"
    )

if not os.path.exists(WARD_FILE):
    raise FileNotFoundError(
        f"Ward geometry file not found: {WARD_FILE}"
    )

print("AQI spatial layer: FOUND")
print("Ward geometry: FOUND")


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading AQI spatial layer...")

aqi = gpd.read_file(AQI_SPATIAL_FILE)

print(f"AQI records: {len(aqi)}")


print("\nLoading ward geometry...")

wards = gpd.read_file(WARD_FILE)

print(f"Ward records: {len(wards)}")
print(f"Ward CRS: {wards.crs}")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

required_aqi = [
    "location_id",
    "station_name",
    "predicted_AQI",
    "AQI_category",
    "geometry"
]

required_wards = [
    "Ward_No",
    "Ward_Name",
    "geometry"
]


for column in required_aqi:
    if column not in aqi.columns:
        raise ValueError(
            f"Missing AQI column: {column}"
        )


for column in required_wards:
    if column not in wards.columns:
        raise ValueError(
            f"Missing ward column: {column}"
        )


print("Required column validation: PASSED")


# ============================================================
# NORMALIZE WARD IDS
# ============================================================

wards["Ward_No"] = pd.to_numeric(
    wards["Ward_No"],
    errors="coerce"
)

wards = wards.dropna(
    subset=["Ward_No"]
)

wards["Ward_No"] = wards["Ward_No"].astype(int)


# ============================================================
# VALIDATE WARDS
# ============================================================

print("\nValidating wards...")

duplicate_wards = wards["Ward_No"].duplicated().sum()

print(f"Duplicate wards: {duplicate_wards}")

if duplicate_wards != 0:
    raise ValueError(
        "Duplicate Ward_No values found."
    )


if len(wards) != 272:
    print(
        f"WARNING: Expected 272 wards, found {len(wards)}"
    )

else:
    print("272 wards found")


# ============================================================
# VALIDATE AQI VALUES
# ============================================================

print("\nPreparing AQI values...")

aqi["predicted_AQI"] = pd.to_numeric(
    aqi["predicted_AQI"],
    errors="coerce"
)

missing_aqi = aqi["predicted_AQI"].isna().sum()

if missing_aqi > 0:
    raise ValueError(
        f"Missing predicted AQI values: {missing_aqi}"
    )


infinite_aqi = (
    ~np.isfinite(aqi["predicted_AQI"])
).sum()

if infinite_aqi > 0:
    raise ValueError(
        f"Infinite AQI values found: {infinite_aqi}"
    )

print("AQI numeric validation: PASSED")


# ============================================================
# CRS
# ============================================================

print("\nChecking CRS...")

if aqi.crs is None:
    raise ValueError(
        "AQI layer has no CRS."
    )

if wards.crs is None:
    raise ValueError(
        "Ward layer has no CRS."
    )

print(f"AQI CRS: {aqi.crs}")
print(f"Ward CRS: {wards.crs}")


# ============================================================
# REPROJECT AQI TO WARD CRS
# ============================================================

if aqi.crs != wards.crs:

    print(
        "\nReprojecting AQI layer to ward CRS..."
    )

    aqi = aqi.to_crs(
        wards.crs
    )

    print("Reprojection completed")


# ============================================================
# SPATIAL JOIN
# ============================================================

print("\nPerforming spatial join...")

# AQI points -> wards
joined = gpd.sjoin(
    aqi,
    wards[
        [
            "Ward_No",
            "Ward_Name",
            "geometry"
        ]
    ],
    how="inner",
    predicate="within"
)

print(
    f"Spatially joined AQI records: {len(joined)}"
)


# ============================================================
# CHECK STATION MATCHING
# ============================================================

if len(joined) == 0:
    raise ValueError(
        "No AQI stations matched with wards."
    )

print("Spatial join validation: PASSED")


# ============================================================
# WARD-LEVEL AQI AGGREGATION
# ============================================================

print("\nAggregating AQI by ward...")

ward_aqi = (
    joined
    .groupby(
        ["Ward_No", "Ward_Name"],
        as_index=False
    )
    .agg(
        mean_predicted_AQI=(
            "predicted_AQI",
            "mean"
        ),
        max_predicted_AQI=(
            "predicted_AQI",
            "max"
        ),
        min_predicted_AQI=(
            "predicted_AQI",
            "min"
        ),
        station_count=(
            "location_id",
            "nunique"
        )
    )
)


# ============================================================
# AQI CATEGORY
# ============================================================

def get_aqi_category(aqi_value):

    if aqi_value <= 50:
        return "Good"

    elif aqi_value <= 100:
        return "Satisfactory"

    elif aqi_value <= 200:
        return "Moderate"

    elif aqi_value <= 300:
        return "Poor"

    elif aqi_value <= 400:
        return "Very Poor"

    else:
        return "Severe"


ward_aqi["AQI_category"] = (
    ward_aqi["mean_predicted_AQI"]
    .apply(get_aqi_category)
)


# ============================================================
# JOIN BACK TO ALL WARDS
# ============================================================

print("\nJoining AQI results with all wards...")

ward_result = wards[
    [
        "Ward_No",
        "Ward_Name",
        "geometry"
    ]
].merge(
    ward_aqi,
    on=[
        "Ward_No",
        "Ward_Name"
    ],
    how="left"
)


# ============================================================
# HANDLE WARDS WITHOUT STATION
# ============================================================

ward_result["station_count"] = (
    ward_result["station_count"]
    .fillna(0)
    .astype(int)
)

print(
    "Wards with direct AQI station coverage:",
    (ward_result["station_count"] > 0).sum()
)

print(
    "Wards without direct AQI station coverage:",
    (ward_result["station_count"] == 0).sum()
)


# ============================================================
# GEOMETRY VALIDATION
# ============================================================

print("\nValidating geometry...")

missing_geometry = (
    ward_result.geometry.isna().sum()
)

invalid_geometry = (
    (~ward_result.geometry.is_valid).sum()
)

print(
    f"Missing geometry: {missing_geometry}"
)

print(
    f"Invalid geometry: {invalid_geometry}"
)

if missing_geometry > 0:
    raise ValueError(
        "Missing ward geometry detected."
    )

if invalid_geometry > 0:
    raise ValueError(
        "Invalid ward geometry detected."
    )

print("Geometry validation: PASSED")


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


print("\nSaving ward AQI GeoJSON...")

ward_result.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)

print(
    f"GeoJSON saved:\n{OUTPUT_GEOJSON}"
)


print("\nSaving ward AQI CSV...")

ward_result.drop(
    columns="geometry"
).to_csv(
    OUTPUT_CSV,
    index=False
)

print(
    f"CSV saved:\n{OUTPUT_CSV}"
)


# ============================================================
# SUMMARY
# ============================================================

category_counts = (
    ward_result["AQI_category"]
    .value_counts(dropna=False)
    .to_dict()
)

summary = {
    "total_wards": int(len(ward_result)),
    "wards_with_station": int(
        (ward_result["station_count"] > 0).sum()
    ),
    "wards_without_station": int(
        (ward_result["station_count"] == 0).sum()
    ),
    "mean_predicted_AQI": (
        float(
            ward_result["mean_predicted_AQI"]
            .mean()
        )
        if ward_result["mean_predicted_AQI"]
        .notna()
        .any()
        else None
    ),
    "aqi_category_distribution": category_counts
}


import json

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


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL WARD AQI VALIDATION")
print("=" * 70)

print(
    f"Wards available: {len(ward_result) == 272}"
)

print(
    "Unique Ward_No:",
    ward_result["Ward_No"].is_unique
)

print(
    "Geometry available:",
    ward_result.geometry.notna().all()
)

print(
    "Geometry valid:",
    ward_result.geometry.is_valid.all()
)

print(
    "AQI categories created:",
    ward_result["AQI_category"].notna().any()
)

print(
    "GeoJSON exists:",
    os.path.exists(OUTPUT_GEOJSON)
)

print(
    "CSV exists:",
    os.path.exists(OUTPUT_CSV)
)

print(
    "Summary exists:",
    os.path.exists(OUTPUT_SUMMARY)
)


print("\n" + "=" * 70)
print("WARD-LEVEL AQI SUMMARY")
print("=" * 70)

print(
    f"Wards: {len(ward_result)}"
)

print(
    f"Wards with AQI stations: "
    f"{(ward_result['station_count'] > 0).sum()}"
)

print(
    f"Wards without direct stations: "
    f"{(ward_result['station_count'] == 0).sum()}"
)

print("\nAQI Category Distribution:")

print(
    ward_result["AQI_category"]
    .value_counts(dropna=False)
)


print("\nOutput files:")

print(OUTPUT_GEOJSON)
print(OUTPUT_CSV)
print(OUTPUT_SUMMARY)

print("\n" + "=" * 70)
print("WARD-LEVEL AQI SPATIAL LAYER CREATED SUCCESSFULLY")
print("=" * 70)