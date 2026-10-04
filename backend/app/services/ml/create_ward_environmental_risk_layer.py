import os
import json
import math
import numpy as np
import pandas as pd
import geopandas as gpd


# ================================================================
# UrbanMind AI - Ward Environmental Risk Layer
# ================================================================

print("=" * 70)
print("UrbanMind AI - Ward Environmental Risk Layer")
print("=" * 70)


# ================================================================
# FILE PATHS
# ================================================================

AQI_FILE = "data/processed/ml/aqi/delhi_ward_aqi_complete.csv"

HEAT_FILE = "data/processed/ml/delhi_ward_heat_risk.csv"

WARD_GEOMETRY_FILE = "data/raw/gis/Delhi_Wards.geojson"

OUTPUT_DIR = "data/processed/ml/environmental"

OUTPUT_GEOJSON = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_environmental_risk.geojson"
)

OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_environmental_risk.csv"
)

OUTPUT_SUMMARY = os.path.join(
    OUTPUT_DIR,
    "environmental_risk_summary.json"
)


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def check_file(path, name):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )

    print(f"{name}: FOUND")


def normalize_ward_id(series):

    # Convert to string first
    result = series.astype(str).str.strip()

    # Convert values such as 1.0 -> 1
    numeric = pd.to_numeric(result, errors="coerce")

    result = result.where(
        numeric.isna(),
        numeric.round().astype("Int64").astype(str)
    )

    return result


def validate_numeric_column(df, column):

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    missing = df[column].isna().sum()

    infinite = np.isinf(
        df[column].to_numpy(dtype=float)
    ).sum()

    if missing > 0:
        raise ValueError(
            f"{column} contains {missing} missing values."
        )

    if infinite > 0:
        raise ValueError(
            f"{column} contains {infinite} infinite values."
        )


# ================================================================
# CHECK INPUT FILES
# ================================================================

print("\nChecking required files...")

check_file(
    AQI_FILE,
    "Complete AQI ward layer"
)

check_file(
    HEAT_FILE,
    "Heat risk layer"
)

check_file(
    WARD_GEOMETRY_FILE,
    "Ward geometry"
)


# ================================================================
# CREATE OUTPUT DIRECTORY
# ================================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ================================================================
# LOAD AQI
# ================================================================

print("\nLoading AQI data...")

aqi = pd.read_csv(AQI_FILE)

print(f"AQI records: {len(aqi)}")

required_aqi_columns = [
    "Ward_No",
    "Ward_Name",
    "final_AQI",
    "AQI_category",
    "aqi_source",
    "station_count",
    "direct_AQI",
    "interpolated_AQI"
]

missing_aqi = [
    col
    for col in required_aqi_columns
    if col not in aqi.columns
]

if missing_aqi:
    raise ValueError(
        f"Missing AQI columns: {missing_aqi}"
    )

print("AQI column validation: PASSED")


# ================================================================
# LOAD HEAT
# ================================================================

print("\nLoading heat data...")

heat = pd.read_csv(HEAT_FILE)

print(f"Heat records: {len(heat)}")

required_heat_columns = [
    "Ward_No",
    "Ward_Name",
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C",
    "heat_pressure_index",
    "emission_pressure_index",
    "traffic_pressure_index",
    "vegetation_mitigation_index",
    "air_pollution_mitigation_potential",
    "urban_intervention_potential"
]

missing_heat = [
    col
    for col in required_heat_columns
    if col not in heat.columns
]

if missing_heat:
    raise ValueError(
        f"Missing heat columns: {missing_heat}"
    )

print("Heat column validation: PASSED")


# ================================================================
# LOAD WARD GEOMETRY
# ================================================================

print("\nLoading ward geometry...")

wards = gpd.read_file(
    WARD_GEOMETRY_FILE
)

print(f"Ward geometry records: {len(wards)}")
print(f"Ward CRS: {wards.crs}")


# ================================================================
# NORMALIZE WARD IDs
# ================================================================

print("\nNormalizing Ward IDs...")

aqi["Ward_No"] = normalize_ward_id(
    aqi["Ward_No"]
)

heat["Ward_No"] = normalize_ward_id(
    heat["Ward_No"]
)

wards["Ward_No"] = normalize_ward_id(
    wards["Ward_No"]
)


# ================================================================
# FILTER VALID NUMERIC WARDS
# ================================================================

print("\nFiltering ward geometry...")

# UrbanMind currently works with 272 numbered wards.
# Delhi_Wards.geojson also contains CANT_* and NDMC_* records.
# These are outside our 272-ward analysis.

numeric_wards = pd.to_numeric(
    wards["Ward_No"],
    errors="coerce"
)

valid_geometry = numeric_wards.notna()

print(
    f"Non-numeric geometry records removed: "
    f"{(~valid_geometry).sum()}"
)

wards = wards.loc[
    valid_geometry
].copy()

# Convert to integer-style Ward_No
wards["Ward_No"] = (
    pd.to_numeric(
        wards["Ward_No"],
        errors="coerce"
    )
    .round()
    .astype(int)
    .astype(str)
)

print(
    f"Numeric ward geometry records: {len(wards)}"
)


# ================================================================
# CHECK DUPLICATES
# ================================================================

print("\nChecking duplicate wards...")

aqi_duplicates = aqi["Ward_No"].duplicated().sum()
heat_duplicates = heat["Ward_No"].duplicated().sum()
geometry_duplicates = wards["Ward_No"].duplicated().sum()

print(f"AQI duplicates      : {aqi_duplicates}")
print(f"Heat duplicates     : {heat_duplicates}")
print(f"Geometry duplicates : {geometry_duplicates}")

if aqi_duplicates > 0:
    raise ValueError(
        "Duplicate Ward_No values found in AQI data."
    )

if heat_duplicates > 0:
    raise ValueError(
        "Duplicate Ward_No values found in heat data."
    )

if geometry_duplicates > 0:
    print(
        "Warning: duplicate numeric geometry wards found."
    )

    # Keep first geometry for duplicate ward IDs
    wards = wards.drop_duplicates(
        subset=["Ward_No"],
        keep="first"
    )


# ================================================================
# CHECK WARD COVERAGE
# ================================================================

print("\nChecking ward coverage...")

aqi_wards = set(aqi["Ward_No"])
heat_wards = set(heat["Ward_No"])
geometry_wards = set(wards["Ward_No"])

print(f"AQI wards      : {len(aqi_wards)}")
print(f"Heat wards     : {len(heat_wards)}")
print(f"Geometry wards : {len(geometry_wards)}")


aqi_missing_geometry = aqi_wards - geometry_wards
heat_missing_geometry = heat_wards - geometry_wards

if aqi_missing_geometry:
    raise ValueError(
        f"AQI wards missing geometry: "
        f"{sorted(aqi_missing_geometry)}"
    )

if heat_missing_geometry:
    raise ValueError(
        f"Heat wards missing geometry: "
        f"{sorted(heat_missing_geometry)}"
    )


# Geometry may contain some wards not used by AQI/Heat.
# Keep only the 272 wards used by our analysis.

target_wards = aqi_wards.intersection(
    heat_wards
)

wards = wards[
    wards["Ward_No"].isin(target_wards)
].copy()

print(
    f"Final analysis wards: {len(wards)}"
)

if len(target_wards) != 272:
    print(
        f"Warning: expected 272 wards, "
        f"found {len(target_wards)}."
    )

print("Ward coverage validation: PASSED")


# ================================================================
# PREPARE AQI
# ================================================================

print("\nPreparing AQI indicators...")

aqi_numeric_columns = [
    "final_AQI",
    "station_count",
    "interpolated_AQI"
]

for column in aqi_numeric_columns:
    validate_numeric_column(
        aqi,
        column
    )

# direct_AQI can legitimately be missing for interpolated wards.
# Therefore it is NOT treated as a required non-null field.

aqi["direct_AQI"] = pd.to_numeric(
    aqi["direct_AQI"],
    errors="coerce"
)


# ================================================================
# PREPARE HEAT
# ================================================================

print("\nPreparing heat indicators...")

heat_numeric_columns = [
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C",
    "heat_pressure_index",
    "emission_pressure_index",
    "traffic_pressure_index",
    "vegetation_mitigation_index",
    "air_pollution_mitigation_potential",
    "urban_intervention_potential"
]

for column in heat_numeric_columns:
    validate_numeric_column(
        heat,
        column
    )


# ================================================================
# SELECT COLUMNS
# ================================================================

aqi_selected = aqi[
    [
        "Ward_No",
        "Ward_Name",
        "final_AQI",
        "AQI_category",
        "aqi_source",
        "station_count",
        "direct_AQI",
        "interpolated_AQI"
    ]
].copy()


heat_selected = heat[
    required_heat_columns
].copy()


# ================================================================
# MERGE AQI + HEAT
# ================================================================

print("\nMerging AQI and heat data...")

environmental = pd.merge(
    aqi_selected,
    heat_selected,
    on="Ward_No",
    how="inner",
    suffixes=("_aqi", "_heat")
)

print(
    f"Records after AQI + heat merge: "
    f"{len(environmental)}"
)

if len(environmental) != 272:
    raise ValueError(
        f"Expected 272 merged wards, "
        f"got {len(environmental)}."
    )

print("AQI + heat merge: PASSED")


# ================================================================
# PREPARE WARD NAME
# ================================================================

environmental["Ward_Name"] = (
    environmental["Ward_Name_aqi"]
    .fillna(environmental["Ward_Name_heat"])
)

environmental.drop(
    columns=[
        "Ward_Name_aqi",
        "Ward_Name_heat"
    ],
    inplace=True
)


# ================================================================
# ENVIRONMENTAL RISK INDICATORS
# ================================================================

print("\nCreating environmental indicators...")


# AQI risk
environmental["AQI_risk_index"] = (
    environmental["final_AQI"] / 500.0
).clip(0, 1)


# Heat risk
environmental["heat_risk_index"] = (
    environmental["heat_pressure_index"]
).clip(0, 1)


# Emission risk
environmental["emission_risk_index"] = (
    environmental["emission_pressure_index"]
).clip(0, 1)


# Traffic risk
environmental["traffic_risk_index"] = (
    environmental["traffic_pressure_index"]
).clip(0, 1)


# Vegetation mitigation is protective.
# Convert it to a risk contribution.
environmental["vegetation_risk_index"] = (
    1 -
    environmental["vegetation_mitigation_index"].clip(0, 1)
)


# Combined environmental risk
environmental["environmental_risk_score"] = (
    0.40 * environmental["AQI_risk_index"]
    +
    0.30 * environmental["heat_risk_index"]
    +
    0.15 * environmental["emission_risk_index"]
    +
    0.10 * environmental["traffic_risk_index"]
    +
    0.05 * environmental["vegetation_risk_index"]
)


environmental["environmental_risk_score"] = (
    environmental["environmental_risk_score"]
    .clip(0, 1)
)


# ================================================================
# RISK CATEGORY
# ================================================================

def risk_category(score):

    if score < 0.20:
        return "Low"

    elif score < 0.40:
        return "Moderate"

    elif score < 0.60:
        return "High"

    elif score < 0.80:
        return "Very High"

    return "Critical"


environmental["environmental_risk_category"] = (
    environmental["environmental_risk_score"]
    .apply(risk_category)
)


# ================================================================
# MISSING VALUE VALIDATION
# ================================================================

print("\nChecking missing values...")

indicator_columns = [
    "final_AQI",
    "interpolated_AQI",
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C",
    "heat_pressure_index",
    "emission_pressure_index",
    "traffic_pressure_index",
    "vegetation_mitigation_index",
    "air_pollution_mitigation_potential",
    "urban_intervention_potential",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score"
]

missing_counts = environmental[
    indicator_columns
].isna().sum()

print(
    missing_counts[
        missing_counts > 0
    ]
)

if missing_counts.sum() > 0:
    raise ValueError(
        "Missing values found in environmental indicators."
    )

print("Missing-value validation: PASSED")


# ================================================================
# INFINITE VALUE VALIDATION
# ================================================================

print("\nChecking infinite values...")

for column in indicator_columns:

    values = environmental[column].to_numpy(
        dtype=float
    )

    infinite_count = np.isinf(values).sum()

    print(
        f"{column}: {infinite_count}"
    )

    if infinite_count > 0:
        raise ValueError(
            f"Infinite values found in {column}."
        )

print("Infinite-value validation: PASSED")


# ================================================================
# MERGE WITH GEOMETRY
# ================================================================

print("\nAttaching ward geometry...")

wards_for_merge = wards[
    [
        "Ward_No",
        "geometry"
    ]
].copy()


environmental_geo = wards_for_merge.merge(
    environmental,
    on="Ward_No",
    how="inner"
)


# Convert to GeoDataFrame
environmental_geo = gpd.GeoDataFrame(
    environmental_geo,
    geometry="geometry",
    crs=wards.crs
)


print(
    f"Environmental geometry records: "
    f"{len(environmental_geo)}"
)


# ================================================================
# GEOMETRY VALIDATION
# ================================================================

missing_geometry = (
    environmental_geo.geometry.isna().sum()
)

invalid_geometry = (
    (~environmental_geo.geometry.is_valid).sum()
)

print(
    f"Missing geometry: {missing_geometry}"
)

print(
    f"Invalid geometry: {invalid_geometry}"
)

if missing_geometry > 0:
    raise ValueError(
        "Missing ward geometry found."
    )

if invalid_geometry > 0:
    raise ValueError(
        "Invalid ward geometry found."
    )

print("Geometry validation: PASSED")


# ================================================================
# FINAL WARD VALIDATION
# ================================================================

unique_wards = (
    environmental_geo["Ward_No"]
    .nunique()
)

if unique_wards != 272:
    raise ValueError(
        f"Expected 272 unique wards, "
        f"found {unique_wards}."
    )

print(
    f"\nFinal wards: {unique_wards}"
)


# ================================================================
# SAVE GEOJSON
# ================================================================

print("\nSaving environmental risk GeoJSON...")

environmental_geo.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)

print(
    f"GeoJSON saved:\n{OUTPUT_GEOJSON}"
)


# ================================================================
# SAVE CSV
# ================================================================

print("\nSaving environmental risk CSV...")

environmental_csv = environmental_geo.drop(
    columns=["geometry"]
)

environmental_csv.to_csv(
    OUTPUT_CSV,
    index=False
)

print(
    f"CSV saved:\n{OUTPUT_CSV}"
)


# ================================================================
# CREATE SUMMARY
# ================================================================

summary = {

    "total_wards": int(unique_wards),

    "aqi_mean": float(
        environmental["final_AQI"].mean()
    ),

    "aqi_min": float(
        environmental["final_AQI"].min()
    ),

    "aqi_max": float(
        environmental["final_AQI"].max()
    ),

    "mean_lst_C": float(
        environmental["mean_LST_C"].mean()
    ),

    "mean_predicted_lst_C": float(
        environmental["predicted_LST_C"].mean()
    ),

    "mean_environmental_risk_score": float(
        environmental[
            "environmental_risk_score"
        ].mean()
    ),

    "risk_category_distribution": (
        environmental[
            "environmental_risk_category"
        ]
        .value_counts()
        .to_dict()
    ),

    "aqi_source_distribution": (
        environmental[
            "aqi_source"
        ]
        .value_counts()
        .to_dict()
    ),

    "geometry_valid": True,

    "missing_values": False,

    "infinite_values": False
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


# ================================================================
# FINAL VALIDATION
# ================================================================

print("\n" + "=" * 70)
print("FINAL ENVIRONMENTAL RISK VALIDATION")
print("=" * 70)

print(
    f"{unique_wards} wards: True"
)

print(
    "AQI available: True"
)

print(
    "Heat indicators available: True"
)

print(
    "Environmental risk score available: True"
)

print(
    "Risk categories available: True"
)

print(
    "No missing indicators: True"
)

print(
    "No infinite indicators: True"
)

print(
    "Geometry available: True"
)

print(
    "Geometry valid: True"
)

print(
    f"GeoJSON exists: "
    f"{os.path.exists(OUTPUT_GEOJSON)}"
)

print(
    f"CSV exists: "
    f"{os.path.exists(OUTPUT_CSV)}"
)

print(
    f"Summary exists: "
    f"{os.path.exists(OUTPUT_SUMMARY)}"
)


# ================================================================
# SUMMARY
# ================================================================

print("\n" + "=" * 70)
print("ENVIRONMENTAL RISK LAYER SUMMARY")
print("=" * 70)

print(
    f"Wards: {unique_wards}"
)

print(
    f"Mean AQI: "
    f"{environmental['final_AQI'].mean():.2f}"
)

print(
    f"Mean LST: "
    f"{environmental['mean_LST_C'].mean():.2f} °C"
)

print(
    f"Mean predicted LST: "
    f"{environmental['predicted_LST_C'].mean():.2f} °C"
)

print(
    f"Mean environmental risk score: "
    f"{environmental['environmental_risk_score'].mean():.3f}"
)

print("\nRisk Category Distribution:")

print(
    environmental[
        "environmental_risk_category"
    ].value_counts()
)


print("\nOutput files:")

print(OUTPUT_GEOJSON)
print(OUTPUT_CSV)
print(OUTPUT_SUMMARY)


print("\n" + "=" * 70)
print(
    "ENVIRONMENTAL RISK LAYER CREATED SUCCESSFULLY"
)
print("=" * 70)