import os
import numpy as np
import pandas as pd
import geopandas as gpd


print("=" * 60)
print("UrbanMind AI - Unified Urban Dataset Creation")
print("=" * 60)


# ============================================================
# Paths
# ============================================================

POPULATION_PATH = (
    "data/processed/population/"
    "delhi_population_ward_gis.geojson"
)

LULC_PATH = (
    "data/processed/satellite/"
    "delhi_ward_lulc.csv"
)

LST_PATH = (
    "data/processed/satellite/"
    "delhi_ward_lst.csv"
)

TRAFFIC_PATH = (
    "data/processed/gis/"
    "delhi_ward_traffic_features.geojson"
)

EMISSION_PATH = (
    "data/processed/emissions/"
    "delhi_ward_emission_features.geojson"
)

POLICY_PATH = (
    "data/processed/policy/"
    "delhi_ward_policy_planning_features.geojson"
)


OUTPUT_DIR = "data/processed/urban"

OUTPUT_GEOJSON = (
    f"{OUTPUT_DIR}/"
    "delhi_unified_urban_dataset.geojson"
)

OUTPUT_CSV = (
    f"{OUTPUT_DIR}/"
    "delhi_unified_urban_dataset.csv"
)


EXPECTED_WARDS = 272


# ============================================================
# Check Input Files
# ============================================================

print("\nChecking input datasets...")

input_files = {
    "Population": POPULATION_PATH,
    "LULC": LULC_PATH,
    "LST": LST_PATH,
    "Traffic": TRAFFIC_PATH,
    "Emission": EMISSION_PATH,
    "Policy": POLICY_PATH
}


for name, path in input_files.items():

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"{name} dataset not found:\n{path}"
        )

    print(f"{name}: FOUND")


# ============================================================
# Load Datasets
# ============================================================

print("\nLoading datasets...")


population = gpd.read_file(
    POPULATION_PATH
)

lulc = pd.read_csv(
    LULC_PATH
)

lst = pd.read_csv(
    LST_PATH
)

traffic = gpd.read_file(
    TRAFFIC_PATH
)

emission = gpd.read_file(
    EMISSION_PATH
)

policy = gpd.read_file(
    POLICY_PATH
)


print("All datasets loaded successfully.")


# ============================================================
# Normalize Ward Numbers
# ============================================================

datasets = {
    "population": population,
    "lulc": lulc,
    "lst": lst,
    "traffic": traffic,
    "emission": emission,
    "policy": policy
}


for name, df in datasets.items():

    df["Ward_No"] = pd.to_numeric(
        df["Ward_No"],
        errors="coerce"
    )

    if df["Ward_No"].isna().any():

        raise ValueError(
            f"{name}: missing Ward_No detected."
        )

    df["Ward_No"] = (
        df["Ward_No"]
        .astype(int)
    )


# ============================================================
# Check Duplicate Wards Before Merge
# ============================================================

print(
    "\nChecking duplicate wards before merging..."
)


for name, df in datasets.items():

    duplicates = (
        df["Ward_No"]
        .duplicated()
        .sum()
    )

    print(
        f"{name}: {duplicates} duplicate wards"
    )

    if duplicates != 0:

        raise ValueError(
            f"{name} contains duplicate wards."
        )


# ============================================================
# Select Population Features
# ============================================================

print(
    "\nPreparing population features..."
)


population_columns = [
    "Ward_No",
    "Ward_Name",
    "TOT_P",
    "No_HH",
    "TOT_M",
    "TOT_F",
    "P_06",
    "P_LIT",
    "P_ILL",
    "geometry"
]


population_available = [
    column
    for column in population_columns
    if column in population.columns
]


population = population[
    population_available
].copy()


# ============================================================
# Select LULC Features
# ============================================================

print(
    "Preparing LULC features..."
)


lulc_columns = [
    "Ward_No",
    "Ward_Name",
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
    "water_surface"
]


lulc_available = [
    column
    for column in lulc_columns
    if column in lulc.columns
]


lulc = lulc[
    lulc_available
].copy()


# ============================================================
# Select LST Features
# ============================================================

print(
    "Preparing LST features..."
)


lst_columns = [
    "Ward_No",
    "Ward_Name",
    "mean_LST_C"
]


lst_available = [
    column
    for column in lst_columns
    if column in lst.columns
]


lst = lst[
    lst_available
].copy()


# ============================================================
# Select Traffic Features
# ============================================================

print(
    "Preparing traffic features..."
)


traffic_columns = [
    "Ward_No",
    "Ward_Name",
    "road_segment_count",
    "oneway_road_segments",
    "total_road_length_km",
    "primary_road_length_km",
    "secondary_road_length_km",
    "tertiary_road_length_km",
    "residential_road_length_km",
    "major_road_length_km",
    "average_road_segment_length_m",
    "oneway_fraction"
]


traffic_available = [
    column
    for column in traffic_columns
    if column in traffic.columns
]


traffic = traffic[
    traffic_available
].copy()


# ============================================================
# Select Emission Features
# ============================================================

print(
    "Preparing emission features..."
)


emission_columns = [
    "Ward_No",
    "Ward_Name",
    "population_density",
    "road_density_km_per_km2",
    "major_road_density_km_per_km2",
    "traffic_pressure_index",
    "built_pressure_index",
    "heat_pressure_index",
    "vegetation_mitigation_index",
    "emission_pressure_index"
]


emission_available = [
    column
    for column in emission_columns
    if column in emission.columns
]


emission = emission[
    emission_available
].copy()


# ============================================================
# Select Policy Features
# ============================================================

print(
    "Preparing policy/planning features..."
)


policy_columns = [
    "Ward_No",
    "Ward_Name",
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


policy_available = [
    column
    for column in policy_columns
    if column in policy.columns
]


policy = policy[
    policy_available
].copy()


# ============================================================
# Remove Repeated Ward_Name Columns
# ============================================================

def remove_ward_name(df):

    if "Ward_Name" in df.columns:

        return df.drop(
            columns=["Ward_Name"]
        )

    return df


lulc = remove_ward_name(lulc)

lst = remove_ward_name(lst)

traffic = remove_ward_name(traffic)

emission = remove_ward_name(emission)

policy = remove_ward_name(policy)


# ============================================================
# Prepare Base GeoDataFrame
# ============================================================

print(
    "\nCreating master ward geometry..."
)


master = population.copy()


# ============================================================
# Merge LULC
# ============================================================

print(
    "Merging LULC..."
)


master = master.merge(
    lulc,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)


print(
    f"After LULC merge: {len(master)} wards"
)


# ============================================================
# Merge LST
# ============================================================

print(
    "Merging LST..."
)


master = master.merge(
    lst,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)


print(
    f"After LST merge: {len(master)} wards"
)


# ============================================================
# Merge Traffic
# ============================================================

print(
    "Merging traffic..."
)


master = master.merge(
    traffic,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)


print(
    f"After traffic merge: {len(master)} wards"
)


# ============================================================
# Merge Emission
# ============================================================

print(
    "Merging emission features..."
)


master = master.merge(
    emission,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)


print(
    f"After emission merge: {len(master)} wards"
)


# ============================================================
# Merge Policy Features
# ============================================================

print(
    "Merging policy/planning features..."
)


master = master.merge(
    policy,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)


print(
    f"After policy merge: {len(master)} wards"
)


# ============================================================
# Restore GeoDataFrame
# ============================================================

print(
    "\nRestoring spatial geometry..."
)


geometry = population[
    ["Ward_No", "geometry"]
].copy()


master = master.drop(
    columns=["geometry"],
    errors="ignore"
)


master = master.merge(
    geometry,
    on="Ward_No",
    how="left",
    validate="one_to_one"
)


master = gpd.GeoDataFrame(
    master,
    geometry="geometry",
    crs=population.crs
)


# ============================================================
# Sort by Ward Number
# ============================================================

master = master.sort_values(
    "Ward_No"
).reset_index(
    drop=True
)


# ============================================================
# Check Ward Count
# ============================================================

print(
    "\nValidating merged ward count..."
)


if len(master) != EXPECTED_WARDS:

    raise ValueError(
        f"Expected {EXPECTED_WARDS} wards, "
        f"found {len(master)}."
    )


if master["Ward_No"].nunique() != EXPECTED_WARDS:

    raise ValueError(
        "Duplicate Ward_No values detected "
        "after merging."
    )


print(
    f"Ward count: {len(master)}"
)

print(
    "Ward uniqueness: PASSED"
)


# ============================================================
# Check Missing Values
# ============================================================

print(
    "\nChecking missing values..."
)


feature_columns = [
    column
    for column in master.columns
    if column not in [
        "Ward_No",
        "Ward_Name",
        "geometry"
    ]
]


missing_summary = (
    master[feature_columns]
    .isna()
    .sum()
)


missing_total = (
    missing_summary.sum()
)


if missing_total != 0:

    print(
        "\nMissing values detected:"
    )

    print(
        missing_summary[
            missing_summary > 0
        ]
    )

    raise ValueError(
        "Unified dataset contains "
        "missing feature values."
    )


print(
    "Missing values: 0"
)


# ============================================================
# Check Infinite Values
# ============================================================

print(
    "\nChecking infinite values..."
)


numeric_columns = master.select_dtypes(
    include=np.number
).columns


infinite_count = np.isinf(
    master[numeric_columns]
    .to_numpy()
).sum()


if infinite_count != 0:

    raise ValueError(
        f"Found {infinite_count} "
        "infinite numeric values."
    )


print(
    "Infinite values: 0"
)


# ============================================================
# Check Geometry
# ============================================================

print(
    "\nChecking geometry..."
)


missing_geometry = (
    master.geometry.isna()
    .sum()
)


invalid_geometry = (
    (~master.geometry.is_valid)
    .sum()
)


print(
    f"Missing geometry: "
    f"{missing_geometry}"
)

print(
    f"Invalid geometry: "
    f"{invalid_geometry}"
)


if missing_geometry != 0:

    raise ValueError(
        "Missing geometry detected."
    )


if invalid_geometry != 0:

    raise ValueError(
        "Invalid geometry detected."
    )


print(
    "Geometry validation: PASSED"
)


# ============================================================
# Create Output Directory
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# Save GeoJSON
# ============================================================

print(
    "\nSaving unified GeoJSON..."
)


master.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)


print(
    f"GeoJSON saved:\n"
    f"{OUTPUT_GEOJSON}"
)


# ============================================================
# Save CSV
# ============================================================

print(
    "\nSaving ML-ready CSV..."
)


csv_data = master.drop(
    columns=["geometry"]
)


csv_data.to_csv(
    OUTPUT_CSV,
    index=False
)


print(
    f"CSV saved:\n"
    f"{OUTPUT_CSV}"
)


# ============================================================
# Final Dataset Information
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "UNIFIED URBAN DATASET SUMMARY"
)

print(
    "=" * 60
)

print(
    f"Number of wards: "
    f"{len(master)}"
)

print(
    f"Number of total columns: "
    f"{len(master.columns)}"
)

print(
    f"Number of feature columns: "
    f"{len(feature_columns)}"
)

print(
    f"Geometry CRS: "
    f"{master.crs}"
)


print(
    "\nDataset columns:"
)

for index, column in enumerate(
    master.columns,
    start=1
):

    print(
        f"{index}. {column}"
    )


# ============================================================
# Final Validation
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "FINAL UNIFIED DATASET VALIDATION"
)

print(
    "=" * 60
)


print(
    f"272 wards: "
    f"{len(master) == 272}"
)

print(
    f"Unique Ward_No: "
    f"{master['Ward_No'].nunique() == 272}"
)

print(
    f"No missing values: "
    f"{missing_total == 0}"
)

print(
    f"No infinite values: "
    f"{infinite_count == 0}"
)

print(
    f"No missing geometry: "
    f"{missing_geometry == 0}"
)

print(
    f"No invalid geometry: "
    f"{invalid_geometry == 0}"
)


if (
    len(master) == 272
    and
    master["Ward_No"].nunique() == 272
    and
    missing_total == 0
    and
    infinite_count == 0
    and
    missing_geometry == 0
    and
    invalid_geometry == 0
):

    print(
        "\nUNIFIED URBAN DATASET "
        "CREATED SUCCESSFULLY"
    )

else:

    raise ValueError(
        "Unified dataset validation failed."
    )


print(
    "\nPhase 2 data integration is complete."
)

print(
    "=" * 60
)