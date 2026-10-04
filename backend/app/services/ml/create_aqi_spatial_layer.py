import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


print("=" * 70)
print("UrbanMind AI - AQI Spatial Layer Creation")
print("=" * 70)


# ============================================================
# 1. FILE PATHS
# ============================================================

prediction_file = (
    "data/processed/ml/aqi/delhi_aqi_predictions.csv"
)

station_file = (
    "data/raw/air_quality/delhi_monitoring_stations.csv"
)

output_dir = "data/processed/ml/aqi"

output_csv = os.path.join(
    output_dir,
    "delhi_aqi_spatial_layer.csv"
)

output_geojson = os.path.join(
    output_dir,
    "delhi_aqi_spatial_layer.geojson"
)

output_summary = os.path.join(
    output_dir,
    "aqi_spatial_layer_summary.json"
)


# ============================================================
# 2. CHECK FILES
# ============================================================

print("\nChecking required files...")

if not os.path.exists(prediction_file):
    raise FileNotFoundError(
        f"AQI prediction file not found:\n{prediction_file}"
    )

if not os.path.exists(station_file):
    raise FileNotFoundError(
        f"Monitoring station file not found:\n{station_file}"
    )

print("AQI predictions: FOUND")
print("Monitoring stations: FOUND")


# ============================================================
# 3. LOAD DATA
# ============================================================

print("\nLoading AQI predictions...")

predictions = pd.read_csv(prediction_file)

print(
    f"Prediction records: {len(predictions)}"
)

print("\nLoading monitoring stations...")

stations = pd.read_csv(station_file)

print(
    f"Station records: {len(stations)}"
)


# ============================================================
# 4. REQUIRED COLUMNS
# ============================================================

print("\nChecking required columns...")

required_prediction_columns = [
    "location_id",
    "station_name",
    "timestamp_local",
    "actual_AQI",
    "predicted_AQI",
    "prediction_error",
    "absolute_error",
    "AQI_category"
]

required_station_columns = [
    "location_id",
    "station_name",
    "latitude",
    "longitude"
]

for column in required_prediction_columns:

    if column not in predictions.columns:
        raise ValueError(
            f"Missing prediction column: {column}"
        )

for column in required_station_columns:

    if column not in stations.columns:
        raise ValueError(
            f"Missing station column: {column}"
        )

print("Prediction columns: PASSED")
print("Station columns: PASSED")


# ============================================================
# 5. NORMALIZE LOCATION IDs
# ============================================================

print("\nNormalizing location IDs...")

predictions["location_id"] = pd.to_numeric(
    predictions["location_id"],
    errors="coerce"
)

stations["location_id"] = pd.to_numeric(
    stations["location_id"],
    errors="coerce"
)

predictions = predictions.dropna(
    subset=["location_id"]
)

stations = stations.dropna(
    subset=["location_id"]
)

predictions["location_id"] = (
    predictions["location_id"].astype(int)
)

stations["location_id"] = (
    stations["location_id"].astype(int)
)

print("Location IDs normalized successfully")


# ============================================================
# 6. VALIDATE STATION COORDINATES
# ============================================================

print("\nValidating station coordinates...")

stations["latitude"] = pd.to_numeric(
    stations["latitude"],
    errors="coerce"
)

stations["longitude"] = pd.to_numeric(
    stations["longitude"],
    errors="coerce"
)

missing_latitude = (
    stations["latitude"].isna().sum()
)

missing_longitude = (
    stations["longitude"].isna().sum()
)

print(
    f"Missing latitude : {missing_latitude}"
)

print(
    f"Missing longitude: {missing_longitude}"
)

if missing_latitude > 0:
    raise ValueError(
        "Missing station latitude values found."
    )

if missing_longitude > 0:
    raise ValueError(
        "Missing station longitude values found."
    )


# ============================================================
# 7. VALIDATE COORDINATE RANGE
# ============================================================

invalid_latitude = (
    (stations["latitude"] < -90) |
    (stations["latitude"] > 90)
).sum()

invalid_longitude = (
    (stations["longitude"] < -180) |
    (stations["longitude"] > 180)
).sum()

print(
    f"Invalid latitude : {invalid_latitude}"
)

print(
    f"Invalid longitude: {invalid_longitude}"
)

if invalid_latitude > 0:
    raise ValueError(
        "Invalid latitude values found."
    )

if invalid_longitude > 0:
    raise ValueError(
        "Invalid longitude values found."
    )

print("Coordinate validation: PASSED")


# ============================================================
# 8. CHECK DUPLICATE STATIONS
# ============================================================

print("\nChecking station duplicates...")

duplicate_count = stations[
    stations["location_id"].duplicated(keep=False)
]["location_id"].nunique()

print(
    f"Duplicate station location IDs: {duplicate_count}"
)

if duplicate_count > 0:
    print(
        "Keeping first metadata record for each location."
    )

    stations = stations.drop_duplicates(
        subset=["location_id"],
        keep="first"
    )

print(
    f"Unique monitoring stations: {len(stations)}"
)


# ============================================================
# 9. CHECK LOCATION COVERAGE
# ============================================================

print("\nChecking AQI station coverage...")

prediction_locations = set(
    predictions["location_id"].unique()
)

station_locations = set(
    stations["location_id"].unique()
)

missing_station_metadata = (
    prediction_locations - station_locations
)

unused_stations = (
    station_locations - prediction_locations
)

print(
    "Prediction locations without station metadata:",
    len(missing_station_metadata)
)

print(
    "Stations without prediction records:",
    len(unused_stations)
)

if len(missing_station_metadata) > 0:

    raise ValueError(
        "Some AQI prediction locations do not have "
        "station coordinates."
    )

print("Station coverage check: PASSED")


# ============================================================
# 10. MERGE AQI + STATION DATA
# ============================================================

print(
    "\nMerging AQI predictions with station coordinates..."
)

station_columns_to_use = [
    "location_id",
    "latitude",
    "longitude",
    "timezone",
    "is_mobile",
    "is_monitor"
]

spatial_data = predictions.merge(
    stations[station_columns_to_use],
    on="location_id",
    how="inner"
)

print(
    f"Records after spatial merge: {len(spatial_data)}"
)


# ============================================================
# 11. CHECK MERGE RESULT
# ============================================================

if len(spatial_data) == 0:

    raise ValueError(
        "No records remained after AQI-station merge."
    )

if len(spatial_data) != len(predictions):

    raise ValueError(
        "Some AQI prediction records were lost "
        "during the station merge."
    )

print("Spatial merge validation: PASSED")


# ============================================================
# 12. PREPARE NUMERIC AQI FEATURES
# ============================================================

print("\nPreparing AQI numeric features...")

numeric_columns = [
    "actual_AQI",
    "predicted_AQI",
    "prediction_error",
    "absolute_error",
    "latitude",
    "longitude"
]

for column in numeric_columns:

    spatial_data[column] = pd.to_numeric(
        spatial_data[column],
        errors="coerce"
    )


# ============================================================
# 13. VALIDATE MISSING VALUES
# ============================================================

print("\nChecking missing values...")

missing_values = spatial_data[
    numeric_columns
].isna().sum()

print(missing_values)

if missing_values.sum() > 0:

    raise ValueError(
        "Missing numeric values detected."
    )

print("Missing-value validation: PASSED")


# ============================================================
# 14. VALIDATE INFINITE VALUES
# ============================================================

print("\nChecking infinite values...")

infinite_total = 0

for column in numeric_columns:

    infinite_count = np.isinf(
        spatial_data[column].to_numpy()
    ).sum()

    print(
        f"{column}: {infinite_count}"
    )

    infinite_total += infinite_count


if infinite_total > 0:

    raise ValueError(
        "Infinite numeric values detected."
    )

print("Infinite-value validation: PASSED")


# ============================================================
# 15. CREATE POINT GEOMETRY
# ============================================================

print("\nCreating station geometries...")

geometry = [
    Point(longitude, latitude)
    for longitude, latitude in zip(
        spatial_data["longitude"],
        spatial_data["latitude"]
    )
]

aqi_gdf = gpd.GeoDataFrame(
    spatial_data,
    geometry=geometry,
    crs="EPSG:4326"
)

print(
    f"Spatial records created: {len(aqi_gdf)}"
)


# ============================================================
# 16. VALIDATE GEOMETRY
# ============================================================

print("\nValidating geometry...")

missing_geometry = (
    aqi_gdf.geometry.isna().sum()
)

invalid_geometry = (
    (~aqi_gdf.geometry.is_valid).sum()
)

print(
    f"Missing geometry: {missing_geometry}"
)

print(
    f"Invalid geometry: {invalid_geometry}"
)

if missing_geometry > 0:

    raise ValueError(
        "Missing station geometry detected."
    )

if invalid_geometry > 0:

    raise ValueError(
        "Invalid station geometry detected."
    )

print("Geometry validation: PASSED")


# ============================================================
# 17. AQI CATEGORY VALIDATION
# ============================================================

print("\nValidating AQI categories...")

missing_categories = (
    aqi_gdf["AQI_category"].isna().sum()
)

print(
    f"Missing AQI categories: {missing_categories}"
)

if missing_categories > 0:

    raise ValueError(
        "Missing AQI categories detected."
    )

print("AQI category validation: PASSED")


# ============================================================
# 18. CATEGORY DISTRIBUTION
# ============================================================

print("\nAQI category distribution:")

category_counts = (
    aqi_gdf["AQI_category"]
    .value_counts()
)

for category, count in category_counts.items():

    print(
        f"{category}: {count} records"
    )


# ============================================================
# 19. CREATE SUMMARY
# ============================================================

aqi_summary = {

    "records": int(
        len(aqi_gdf)
    ),

    "unique_locations": int(
        aqi_gdf["location_id"].nunique()
    ),

    "unique_stations": int(
        aqi_gdf["station_name"].nunique()
    ),

    "mean_actual_AQI": float(
        aqi_gdf["actual_AQI"].mean()
    ),

    "mean_predicted_AQI": float(
        aqi_gdf["predicted_AQI"].mean()
    ),

    "minimum_predicted_AQI": float(
        aqi_gdf["predicted_AQI"].min()
    ),

    "maximum_predicted_AQI": float(
        aqi_gdf["predicted_AQI"].max()
    ),

    "crs": "EPSG:4326",

    "category_distribution": {
        str(category): int(count)
        for category, count
        in category_counts.items()
    }
}


# ============================================================
# 20. CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    output_dir,
    exist_ok=True
)


# ============================================================
# 21. SAVE CSV
# ============================================================

print("\nSaving AQI spatial CSV...")

csv_data = aqi_gdf.drop(
    columns=["geometry"]
)

csv_data.to_csv(
    output_csv,
    index=False
)

print(
    f"CSV saved:\n{output_csv}"
)


# ============================================================
# 22. SAVE GEOJSON
# ============================================================

print("\nSaving AQI spatial GeoJSON...")

aqi_gdf.to_file(
    output_geojson,
    driver="GeoJSON"
)

print(
    f"GeoJSON saved:\n{output_geojson}"
)


# ============================================================
# 23. SAVE SUMMARY JSON
# ============================================================

print("\nSaving AQI spatial summary...")

with open(
    output_summary,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        aqi_summary,
        file,
        indent=4
    )

print(
    f"Summary saved:\n{output_summary}"
)


# ============================================================
# 24. FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL AQI SPATIAL LAYER VALIDATION")
print("=" * 70)

print(
    "Records available:",
    len(aqi_gdf) > 0
)

print(
    "Unique locations:",
    aqi_gdf["location_id"].nunique()
)

print(
    "Coordinates available:",
    (
        aqi_gdf["latitude"].notna().all()
        and
        aqi_gdf["longitude"].notna().all()
    )
)

print(
    "Predictions available:",
    aqi_gdf["predicted_AQI"].notna().all()
)

print(
    "AQI categories available:",
    aqi_gdf["AQI_category"].notna().all()
)

print(
    "No missing geometry:",
    aqi_gdf.geometry.notna().all()
)

print(
    "No invalid geometry:",
    aqi_gdf.geometry.is_valid.all()
)

print(
    "No infinite AQI values:",
    not np.isinf(
        aqi_gdf["predicted_AQI"].to_numpy()
    ).any()
)

print(
    "CSV exists:",
    os.path.exists(output_csv)
)

print(
    "GeoJSON exists:",
    os.path.exists(output_geojson)
)

print(
    "Summary exists:",
    os.path.exists(output_summary)
)


# ============================================================
# 25. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("AQI SPATIAL LAYER SUMMARY")
print("=" * 70)

print(
    f"Records: {len(aqi_gdf)}"
)

print(
    f"Stations: "
    f"{aqi_gdf['station_name'].nunique()}"
)

print(
    f"Location IDs: "
    f"{aqi_gdf['location_id'].nunique()}"
)

print(
    f"Predicted AQI range: "
    f"{aqi_gdf['predicted_AQI'].min():.2f} - "
    f"{aqi_gdf['predicted_AQI'].max():.2f}"
)

print(
    f"Mean predicted AQI: "
    f"{aqi_gdf['predicted_AQI'].mean():.2f}"
)

print("\nOutput files:")

print(output_csv)
print(output_geojson)
print(output_summary)

print("\n" + "=" * 70)
print("AQI SPATIAL LAYER CREATED SUCCESSFULLY")
print("=" * 70)