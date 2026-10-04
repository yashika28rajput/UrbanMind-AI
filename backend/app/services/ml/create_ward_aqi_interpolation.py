import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


print("=" * 70)
print("UrbanMind AI - Complete Ward AQI Interpolation")
print("=" * 70)


# ============================================================
# PATHS
# ============================================================

AQI_STATIONS_FILE = (
    "data/processed/ml/aqi/delhi_aqi_spatial_layer.geojson"
)

WARD_AQI_FILE = (
    "data/processed/ml/aqi/delhi_ward_aqi.geojson"
)

OUTPUT_DIR = "data/processed/ml/aqi"

OUTPUT_GEOJSON = (
    f"{OUTPUT_DIR}/delhi_ward_aqi_complete.geojson"
)

OUTPUT_CSV = (
    f"{OUTPUT_DIR}/delhi_ward_aqi_complete.csv"
)

OUTPUT_SUMMARY = (
    f"{OUTPUT_DIR}/ward_aqi_interpolation_summary.json"
)


# ============================================================
# CHECK FILES
# ============================================================

print("\nChecking required files...")

if not os.path.exists(AQI_STATIONS_FILE):
    raise FileNotFoundError(
        f"AQI station layer not found:\n{AQI_STATIONS_FILE}"
    )

if not os.path.exists(WARD_AQI_FILE):
    raise FileNotFoundError(
        f"Ward AQI layer not found:\n{WARD_AQI_FILE}"
    )

print("AQI station layer: FOUND")
print("Ward AQI layer: FOUND")


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading AQI station data...")

stations = gpd.read_file(
    AQI_STATIONS_FILE
)

print(
    f"AQI records: {len(stations)}"
)


print("\nLoading ward AQI layer...")

wards = gpd.read_file(
    WARD_AQI_FILE
)

print(
    f"Ward records: {len(wards)}"
)


# ============================================================
# VALIDATE COLUMNS
# ============================================================

required_station_columns = [
    "location_id",
    "station_name",
    "predicted_AQI",
    "geometry"
]

required_ward_columns = [
    "Ward_No",
    "Ward_Name",
    "geometry"
]

for column in required_station_columns:

    if column not in stations.columns:

        raise ValueError(
            f"Missing station column: {column}"
        )


for column in required_ward_columns:

    if column not in wards.columns:

        raise ValueError(
            f"Missing ward column: {column}"
        )

print(
    "Required column validation: PASSED"
)


# ============================================================
# PREPARE STATION DATA
# ============================================================

print("\nPreparing AQI stations...")

stations["predicted_AQI"] = pd.to_numeric(
    stations["predicted_AQI"],
    errors="coerce"
)

stations = stations.dropna(
    subset=[
        "predicted_AQI",
        "geometry"
    ]
)

stations = stations[
    np.isfinite(
        stations["predicted_AQI"]
    )
].copy()

print(
    f"Valid station records: {len(stations)}"
)


# ============================================================
# CONVERT TO POINTS
# ============================================================

print("\nPreparing station coordinates...")

stations = stations.to_crs(
    "EPSG:3857"
)

wards = wards.to_crs(
    "EPSG:3857"
)

# Station geometry should already be points.
# To avoid duplicate hourly observations affecting
# interpolation, aggregate by location.

station_points = (
    stations
    .groupby(
        "location_id",
        as_index=False
    )
    .agg(
        station_name=(
            "station_name",
            "first"
        ),
        predicted_AQI=(
            "predicted_AQI",
            "mean"
        ),
        geometry=(
            "geometry",
            "first"
        )
    )
)

station_points = gpd.GeoDataFrame(
    station_points,
    geometry="geometry",
    crs="EPSG:3857"
)

print(
    f"Unique AQI stations: {len(station_points)}"
)


# ============================================================
# CREATE WARD CENTROIDS
# ============================================================

print("\nCreating ward centroids...")

wards["ward_centroid"] = (
    wards.geometry.centroid
)

print(
    "Ward centroid creation: PASSED"
)


# ============================================================
# IDW FUNCTION
# ============================================================

def calculate_idw(
    ward_point,
    station_points,
    power=2,
    max_stations=8
):

    distances = (
        station_points.geometry
        .distance(ward_point)
    )

    # Exact station location
    if (distances == 0).any():

        index = distances[
            distances == 0
        ].index[0]

        return float(
            station_points.loc[
                index,
                "predicted_AQI"
            ]
        )

    # Nearest stations
    nearest_indexes = (
        distances
        .sort_values()
        .head(max_stations)
        .index
    )

    nearest_distances = (
        distances.loc[
            nearest_indexes
        ].values
    )

    nearest_values = (
        station_points.loc[
            nearest_indexes,
            "predicted_AQI"
        ].values
    )

    weights = 1 / (
        nearest_distances ** power
    )

    return float(
        np.sum(
            weights * nearest_values
        )
        /
        np.sum(weights)
    )


# ============================================================
# DIRECT AQI LOOKUP
# ============================================================

print("\nPreparing direct station AQI values...")

direct_aqi = wards[
    [
        "Ward_No",
        "Ward_Name",
        "mean_predicted_AQI",
        "station_count"
    ]
].copy()

direct_aqi = direct_aqi.rename(
    columns={
        "mean_predicted_AQI":
            "direct_AQI"
    }
)

direct_aqi["direct_AQI"] = pd.to_numeric(
    direct_aqi["direct_AQI"],
    errors="coerce"
)

direct_aqi["station_count"] = (
    pd.to_numeric(
        direct_aqi["station_count"],
        errors="coerce"
    )
    .fillna(0)
    .astype(int)
)


# ============================================================
# INTERPOLATE ALL WARDS
# ============================================================

print("\nRunning IDW interpolation...")

interpolated_values = []

for index, row in wards.iterrows():

    value = calculate_idw(
        row["ward_centroid"],
        station_points,
        power=2,
        max_stations=8
    )

    interpolated_values.append(
        value
    )


wards["interpolated_AQI"] = (
    interpolated_values
)

print(
    "IDW interpolation: PASSED"
)


# ============================================================
# MERGE DIRECT + INTERPOLATED AQI
# ============================================================

print("\nCreating complete ward AQI layer...")

result = wards[
    [
        "Ward_No",
        "Ward_Name",
        "geometry",
        "interpolated_AQI"
    ]
].copy()

result = result.merge(
    direct_aqi[
        [
            "Ward_No",
            "direct_AQI",
            "station_count"
        ]
    ],
    on="Ward_No",
    how="left"
)


# ============================================================
# CHOOSE FINAL AQI
# ============================================================

result["station_count"] = (
    result["station_count"]
    .fillna(0)
    .astype(int)
)

result["final_AQI"] = np.where(
    result["station_count"] > 0,
    result["direct_AQI"],
    result["interpolated_AQI"]
)

result["aqi_source"] = np.where(
    result["station_count"] > 0,
    "direct_station",
    "interpolated"
)


# ============================================================
# AQI CATEGORY
# ============================================================

def get_aqi_category(value):

    if pd.isna(value):
        return "Unknown"

    if value <= 50:
        return "Good"

    elif value <= 100:
        return "Satisfactory"

    elif value <= 200:
        return "Moderate"

    elif value <= 300:
        return "Poor"

    elif value <= 400:
        return "Very Poor"

    else:
        return "Severe"


result["AQI_category"] = (
    result["final_AQI"]
    .apply(get_aqi_category)
)


# ============================================================
# NUMERIC VALIDATION
# ============================================================

print("\nValidating final AQI values...")

result["final_AQI"] = pd.to_numeric(
    result["final_AQI"],
    errors="coerce"
)

missing_aqi = (
    result["final_AQI"].isna().sum()
)

infinite_aqi = (
    ~np.isfinite(
        result["final_AQI"]
    )
).sum()

print(
    f"Missing AQI: {missing_aqi}"
)

print(
    f"Infinite AQI: {infinite_aqi}"
)

if missing_aqi > 0:
    raise ValueError(
        "Missing final AQI values found."
    )

if infinite_aqi > 0:
    raise ValueError(
        "Infinite final AQI values found."
    )

print(
    "AQI validation: PASSED"
)


# ============================================================
# GEOMETRY VALIDATION
# ============================================================

print("\nValidating ward geometry...")

missing_geometry = (
    result.geometry.isna().sum()
)

invalid_geometry = (
    (~result.geometry.is_valid).sum()
)

print(
    f"Missing geometry: {missing_geometry}"
)

print(
    f"Invalid geometry: {invalid_geometry}"
)

if missing_geometry > 0:
    raise ValueError(
        "Missing ward geometry."
    )

if invalid_geometry > 0:
    raise ValueError(
        "Invalid ward geometry."
    )

print(
    "Geometry validation: PASSED"
)


# ============================================================
# FINAL WARD VALIDATION
# ============================================================

print("\nValidating ward coverage...")

if len(result) != 272:

    raise ValueError(
        f"Expected 272 wards, found {len(result)}"
    )

if not result["Ward_No"].is_unique:

    raise ValueError(
        "Duplicate Ward_No detected."
    )

print(
    "272 wards: PASSED"
)

print(
    "Unique Ward_No: PASSED"
)


# ============================================================
# RETURN TO WGS84
# ============================================================

result = result.to_crs(
    "EPSG:4326"
)


# ============================================================
# SELECT FINAL COLUMNS
# ============================================================

result = result[
    [
        "Ward_No",
        "Ward_Name",
        "final_AQI",
        "AQI_category",
        "aqi_source",
        "station_count",
        "direct_AQI",
        "interpolated_AQI",
        "geometry"
    ]
]


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


print("\nSaving complete ward AQI GeoJSON...")

result.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)

print(
    f"GeoJSON saved:\n{OUTPUT_GEOJSON}"
)


print("\nSaving complete ward AQI CSV...")

result.drop(
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

source_distribution = (
    result["aqi_source"]
    .value_counts()
    .to_dict()
)

category_distribution = (
    result["AQI_category"]
    .value_counts()
    .to_dict()
)

summary = {

    "total_wards":
        int(len(result)),

    "direct_station_wards":
        int(
            (
                result["aqi_source"]
                == "direct_station"
            ).sum()
        ),

    "interpolated_wards":
        int(
            (
                result["aqi_source"]
                == "interpolated"
            ).sum()
        ),

    "mean_final_AQI":
        float(
            result["final_AQI"].mean()
        ),

    "minimum_final_AQI":
        float(
            result["final_AQI"].min()
        ),

    "maximum_final_AQI":
        float(
            result["final_AQI"].max()
        ),

    "aqi_source_distribution":
        source_distribution,

    "aqi_category_distribution":
        category_distribution
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
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("COMPLETE WARD AQI SUMMARY")
print("=" * 70)

print(
    f"Total wards: {len(result)}"
)

print(
    "Direct station wards:",
    (
        result["aqi_source"]
        == "direct_station"
    ).sum()
)

print(
    "Interpolated wards:",
    (
        result["aqi_source"]
        == "interpolated"
    ).sum()
)

print(
    f"Final AQI range: "
    f"{result['final_AQI'].min():.2f} - "
    f"{result['final_AQI'].max():.2f}"
)

print(
    f"Mean final AQI: "
    f"{result['final_AQI'].mean():.2f}"
)

print("\nAQI Category Distribution:")

print(
    result["AQI_category"]
    .value_counts()
)

print("\nAQI Source Distribution:")

print(
    result["aqi_source"]
    .value_counts()
)


# ============================================================
# FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL COMPLETE AQI LAYER VALIDATION")
print("=" * 70)

print(
    "272 wards:",
    len(result) == 272
)

print(
    "Unique Ward_No:",
    result["Ward_No"].is_unique
)

print(
    "No missing AQI:",
    result["final_AQI"].notna().all()
)

print(
    "No infinite AQI:",
    np.isfinite(
        result["final_AQI"]
    ).all()
)

print(
    "AQI categories available:",
    result["AQI_category"].notna().all()
)

print(
    "AQI source available:",
    result["aqi_source"].notna().all()
)

print(
    "Geometry available:",
    result.geometry.notna().all()
)

print(
    "Geometry valid:",
    result.geometry.is_valid.all()
)

print(
    "GeoJSON exists:",
    os.path.exists(
        OUTPUT_GEOJSON
    )
)

print(
    "CSV exists:",
    os.path.exists(
        OUTPUT_CSV
    )
)

print(
    "Summary exists:",
    os.path.exists(
        OUTPUT_SUMMARY
    )
)


print("\n" + "=" * 70)
print(
    "COMPLETE WARD AQI LAYER CREATED SUCCESSFULLY"
)
print("=" * 70)