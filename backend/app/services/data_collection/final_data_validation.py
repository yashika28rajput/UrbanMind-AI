import os
import numpy as np
import pandas as pd
import geopandas as gpd


print("=" * 55)
print("UrbanMind AI - Final Phase 2 Data Validation")
print("=" * 55)


# =========================================================
# Dataset Paths
# =========================================================

DATASETS = {
    "population": (
        "data/processed/population/"
        "delhi_population_ward_gis.geojson"
    ),

    "lulc": (
        "data/processed/satellite/"
        "delhi_ward_lulc.csv"
    ),

    "lst": (
        "data/processed/satellite/"
        "delhi_ward_lst.csv"
    ),

    "traffic": (
        "data/processed/gis/"
        "delhi_ward_traffic_features.geojson"
    ),

    "emission": (
        "data/processed/emissions/"
        "delhi_ward_emission_features.geojson"
    ),

    "policy": (
        "data/processed/policy/"
        "delhi_ward_policy_planning_features.geojson"
    )
}


EXPECTED_WARDS = 272


# =========================================================
# Helper Functions
# =========================================================

def normalize_ward_id(df):
    """
    Normalize Ward_No to int64.
    """

    df = df.copy()

    df["Ward_No"] = pd.to_numeric(
        df["Ward_No"],
        errors="coerce"
    )

    return df


def check_file_exists(path):
    """
    Check whether dataset exists.
    """

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )


def check_ward_structure(
    name,
    df
):
    """
    Validate ward ID structure.
    """

    print(
        f"\n{name.upper()} STRUCTURE"
    )

    records = len(df)

    unique_wards = (
        df["Ward_No"]
        .nunique()
    )

    missing_wards = (
        df["Ward_No"]
        .isna()
        .sum()
    )

    duplicates = (
        df["Ward_No"]
        .duplicated()
        .sum()
    )

    print(
        f"Records: {records}"
    )

    print(
        f"Unique wards: {unique_wards}"
    )

    print(
        f"Missing Ward_No: {missing_wards}"
    )

    print(
        f"Duplicate wards: {duplicates}"
    )

    if records != EXPECTED_WARDS:

        raise ValueError(
            f"{name}: expected "
            f"{EXPECTED_WARDS} records, "
            f"found {records}"
        )

    if unique_wards != EXPECTED_WARDS:

        raise ValueError(
            f"{name}: expected "
            f"{EXPECTED_WARDS} unique wards, "
            f"found {unique_wards}"
        )

    if missing_wards != 0:

        raise ValueError(
            f"{name}: missing Ward_No values"
        )

    if duplicates != 0:

        raise ValueError(
            f"{name}: duplicate wards detected"
        )

    print(
        f"{name}: ward structure PASSED"
    )


# =========================================================
# Check Files
# =========================================================

print("\nChecking dataset files...")

for name, path in DATASETS.items():

    check_file_exists(path)

    print(
        f"{name}: FOUND"
    )


# =========================================================
# Load Datasets
# =========================================================

print(
    "\nLoading all Phase 2 datasets..."
)


population_gdf = gpd.read_file(
    DATASETS["population"]
)

lulc = pd.read_csv(
    DATASETS["lulc"]
)

lst = pd.read_csv(
    DATASETS["lst"]
)

traffic_gdf = gpd.read_file(
    DATASETS["traffic"]
)

emission_gdf = gpd.read_file(
    DATASETS["emission"]
)

policy_gdf = gpd.read_file(
    DATASETS["policy"]
)


print(
    "All datasets loaded successfully"
)


# =========================================================
# Normalize Ward IDs
# =========================================================

population_gdf = normalize_ward_id(
    population_gdf
)

lulc = normalize_ward_id(
    lulc
)

lst = normalize_ward_id(
    lst
)

traffic_gdf = normalize_ward_id(
    traffic_gdf
)

emission_gdf = normalize_ward_id(
    emission_gdf
)

policy_gdf = normalize_ward_id(
    policy_gdf
)


# =========================================================
# Validate Ward Structure
# =========================================================

check_ward_structure(
    "Population",
    population_gdf
)

check_ward_structure(
    "LULC",
    lulc
)

check_ward_structure(
    "LST",
    lst
)

check_ward_structure(
    "Traffic",
    traffic_gdf
)

check_ward_structure(
    "Emission",
    emission_gdf
)

check_ward_structure(
    "Policy",
    policy_gdf
)


# =========================================================
# Ward Coverage Consistency
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "CHECKING WARD COVERAGE CONSISTENCY"
)

print(
    "=" * 55
)


ward_sets = {

    "population": set(
        population_gdf[
            "Ward_No"
        ].dropna().astype(int)
    ),

    "lulc": set(
        lulc[
            "Ward_No"
        ].dropna().astype(int)
    ),

    "lst": set(
        lst[
            "Ward_No"
        ].dropna().astype(int)
    ),

    "traffic": set(
        traffic_gdf[
            "Ward_No"
        ].dropna().astype(int)
    ),

    "emission": set(
        emission_gdf[
            "Ward_No"
        ].dropna().astype(int)
    ),

    "policy": set(
        policy_gdf[
            "Ward_No"
        ].dropna().astype(int)
    )
}


reference_wards = ward_sets[
    "population"
]


coverage_passed = True


for name, wards in ward_sets.items():

    missing = (
        reference_wards - wards
    )

    extra = (
        wards - reference_wards
    )

    print(
        f"\n{name.upper()}:"
    )

    print(
        f"Missing wards: {len(missing)}"
    )

    print(
        f"Extra wards: {len(extra)}"
    )

    if missing or extra:

        coverage_passed = False


if not coverage_passed:

    raise ValueError(
        "Ward coverage mismatch detected"
    )


print(
    "\nWard coverage consistency PASSED"
)


# =========================================================
# Population Validation
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "VALIDATING POPULATION DATA"
)

print(
    "=" * 55
)


population_numeric = [
    "TOT_P",
    "No_HH",
    "TOT_M",
    "TOT_F"
]


for column in population_numeric:

    if column not in population_gdf.columns:

        raise KeyError(
            f"Missing population column: "
            f"{column}"
        )

    population_gdf[column] = pd.to_numeric(
        population_gdf[column],
        errors="coerce"
    )


for column in population_numeric:

    missing = (
        population_gdf[column]
        .isna()
        .sum()
    )

    negative = (
        population_gdf[column] < 0
    ).sum()

    print(
        f"{column}: "
        f"missing={missing}, "
        f"negative={negative}"
    )

    if missing != 0:

        raise ValueError(
            f"Missing values in {column}"
        )

    if negative != 0:

        raise ValueError(
            f"Negative values in {column}"
        )


male_female_difference = (
    population_gdf["TOT_M"]
    +
    population_gdf["TOT_F"]
    -
    population_gdf["TOT_P"]
)


mismatch_count = (
    male_female_difference
    .abs()
    .gt(0)
    .sum()
)


print(
    f"Male + Female mismatch: "
    f"{mismatch_count}"
)


if mismatch_count != 0:

    raise ValueError(
        "Population gender totals do not match"
    )


print(
    "Population validation PASSED"
)


# =========================================================
# Geometry Validation
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "VALIDATING GEOMETRIES"
)

print(
    "=" * 55
)


geometry_datasets = {
    "population": population_gdf,
    "traffic": traffic_gdf,
    "emission": emission_gdf,
    "policy": policy_gdf
}


for name, gdf in geometry_datasets.items():

    missing_geometry = (
        gdf.geometry.isna()
        .sum()
    )

    invalid_geometry = (
        (~gdf.geometry.is_valid)
        .sum()
    )

    print(
        f"{name.upper()}: "
        f"missing={missing_geometry}, "
        f"invalid={invalid_geometry}"
    )

    if missing_geometry != 0:

        raise ValueError(
            f"{name}: missing geometries"
        )

    if invalid_geometry != 0:

        raise ValueError(
            f"{name}: invalid geometries"
        )


print(
    "Geometry validation PASSED"
)


# =========================================================
# LULC Validation
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "VALIDATING LULC DATA"
)

print(
    "=" * 55
)


lulc_columns = [
    "water",
    "trees",
    "grass",
    "flooded_vegetation",
    "crops",
    "shrub_and_scrub",
    "built",
    "bare",
    "snow_and_ice"
]


for column in lulc_columns:

    if column not in lulc.columns:

        raise KeyError(
            f"Missing LULC column: "
            f"{column}"
        )

    lulc[column] = pd.to_numeric(
        lulc[column],
        errors="coerce"
    )

    missing = (
        lulc[column]
        .isna()
        .sum()
    )

    below_zero = (
        lulc[column] < 0
    ).sum()

    above_one = (
        lulc[column] > 1
    ).sum()

    print(
        f"{column}: "
        f"missing={missing}, "
        f"<0={below_zero}, "
        f">1={above_one}"
    )

    if missing != 0:

        raise ValueError(
            f"LULC missing values: "
            f"{column}"
        )

    if below_zero != 0:

        raise ValueError(
            f"LULC values below 0: "
            f"{column}"
        )

    if above_one != 0:

        raise ValueError(
            f"LULC values above 1: "
            f"{column}"
        )


print(
    "LULC validation PASSED"
)


# =========================================================
# LST Validation
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "VALIDATING LST DATA"
)

print(
    "=" * 55
)


if "mean_LST_C" not in lst.columns:

    raise KeyError(
        "mean_LST_C missing"
    )


lst["mean_LST_C"] = pd.to_numeric(
    lst["mean_LST_C"],
    errors="coerce"
)


lst_missing = (
    lst["mean_LST_C"]
    .isna()
    .sum()
)

lst_infinite = (
    np.isinf(
        lst["mean_LST_C"]
    ).sum()
)


print(
    f"Missing LST: {lst_missing}"
)

print(
    f"Infinite LST: {lst_infinite}"
)

print(
    f"Minimum LST: "
    f"{lst['mean_LST_C'].min():.2f} C"
)

print(
    f"Maximum LST: "
    f"{lst['mean_LST_C'].max():.2f} C"
)


if lst_missing != 0:

    raise ValueError(
        "Missing LST values"
    )

if lst_infinite != 0:

    raise ValueError(
        "Infinite LST values"
    )


print(
    "LST validation PASSED"
)


# =========================================================
# Traffic Validation
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "VALIDATING TRAFFIC DATA"
)

print(
    "=" * 55
)


traffic_numeric = [
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


for column in traffic_numeric:

    if column not in traffic_gdf.columns:

        raise KeyError(
            f"Missing traffic column: "
            f"{column}"
        )

    traffic_gdf[column] = pd.to_numeric(
        traffic_gdf[column],
        errors="coerce"
    )

    missing = (
        traffic_gdf[column]
        .isna()
        .sum()
    )

    infinite = (
        np.isinf(
            traffic_gdf[column]
        ).sum()
    )

    negative = (
        traffic_gdf[column] < 0
    ).sum()

    print(
        f"{column}: "
        f"missing={missing}, "
        f"negative={negative}, "
        f"infinite={infinite}"
    )

    if missing != 0:

        raise ValueError(
            f"Missing traffic values: "
            f"{column}"
        )

    if negative != 0:

        raise ValueError(
            f"Negative traffic values: "
            f"{column}"
        )

    if infinite != 0:

        raise ValueError(
            f"Infinite traffic values: "
            f"{column}"
        )


oneway_invalid = (
    (
        traffic_gdf[
            "oneway_fraction"
        ] < 0
    )
    |
    (
        traffic_gdf[
            "oneway_fraction"
        ] > 1
    )
).sum()


print(
    f"Invalid one-way fractions: "
    f"{oneway_invalid}"
)


if oneway_invalid != 0:

    raise ValueError(
        "Invalid one-way fraction"
    )


print(
    "Traffic validation PASSED"
)


# =========================================================
# Emission Validation
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "VALIDATING EMISSION FEATURES"
)

print(
    "=" * 55
)


emission_indices = [
    "traffic_pressure_index",
    "built_pressure_index",
    "heat_pressure_index",
    "vegetation_mitigation_index",
    "emission_pressure_index"
]


for column in emission_indices:

    if column not in emission_gdf.columns:

        raise KeyError(
            f"Missing emission index: "
            f"{column}"
        )

    emission_gdf[column] = pd.to_numeric(
        emission_gdf[column],
        errors="coerce"
    )

    missing = (
        emission_gdf[column]
        .isna()
        .sum()
    )

    infinite = (
        np.isinf(
            emission_gdf[column]
        ).sum()
    )

    below_zero = (
        emission_gdf[column] < 0
    ).sum()

    above_one = (
        emission_gdf[column] > 1
    ).sum()

    print(
        f"{column}: "
        f"missing={missing}, "
        f"<0={below_zero}, "
        f">1={above_one}, "
        f"infinite={infinite}"
    )

    if missing != 0:

        raise ValueError(
            f"Missing emission index: "
            f"{column}"
        )

    if infinite != 0:

        raise ValueError(
            f"Infinite emission index: "
            f"{column}"
        )

    if below_zero != 0:

        raise ValueError(
            f"Negative emission index: "
            f"{column}"
        )

    if above_one != 0:

        raise ValueError(
            f"Emission index > 1: "
            f"{column}"
        )


print(
    "Emission validation PASSED"
)


# =========================================================
# Policy Validation
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "VALIDATING POLICY FEATURES"
)

print(
    "=" * 55
)


policy_indices = [
    "green_cover_intervention_potential",
    "cool_roof_intervention_potential",
    "urban_forest_potential",
    "roadside_greening_potential",
    "water_body_restoration_potential",
    "heat_mitigation_potential",
    "air_pollution_mitigation_potential",
    "sustainable_mobility_potential",
    "urban_intervention_potential"
]


for column in policy_indices:

    if column not in policy_gdf.columns:

        raise KeyError(
            f"Missing policy feature: "
            f"{column}"
        )

    policy_gdf[column] = pd.to_numeric(
        policy_gdf[column],
        errors="coerce"
    )

    missing = (
        policy_gdf[column]
        .isna()
        .sum()
    )

    infinite = (
        np.isinf(
            policy_gdf[column]
        ).sum()
    )

    below_zero = (
        policy_gdf[column] < 0
    ).sum()

    above_one = (
        policy_gdf[column] > 1
    ).sum()

    print(
        f"{column}: "
        f"missing={missing}, "
        f"<0={below_zero}, "
        f">1={above_one}, "
        f"infinite={infinite}"
    )

    if missing != 0:

        raise ValueError(
            f"Missing policy feature: "
            f"{column}"
        )

    if infinite != 0:

        raise ValueError(
            f"Infinite policy feature: "
            f"{column}"
        )

    if below_zero != 0:

        raise ValueError(
            f"Negative policy feature: "
            f"{column}"
        )

    if above_one != 0:

        raise ValueError(
            f"Policy feature > 1: "
            f"{column}"
        )


print(
    "Policy validation PASSED"
)


# =========================================================
# Cross-Dataset Consistency
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "CROSS-DATASET CONSISTENCY CHECK"
)

print(
    "=" * 55
)


population_wards = set(
    population_gdf[
        "Ward_No"
    ].astype(int)
)

lulc_wards = set(
    lulc[
        "Ward_No"
    ].astype(int)
)

lst_wards = set(
    lst[
        "Ward_No"
    ].astype(int)
)

traffic_wards = set(
    traffic_gdf[
        "Ward_No"
    ].astype(int)
)

emission_wards = set(
    emission_gdf[
        "Ward_No"
    ].astype(int)
)

policy_wards = set(
    policy_gdf[
        "Ward_No"
    ].astype(int)
)


all_equal = (
    population_wards
    ==
    lulc_wards
    ==
    lst_wards
    ==
    traffic_wards
    ==
    emission_wards
    ==
    policy_wards
)


print(
    f"Population = LULC: "
    f"{population_wards == lulc_wards}"
)

print(
    f"LULC = LST: "
    f"{lulc_wards == lst_wards}"
)

print(
    f"LST = Traffic: "
    f"{lst_wards == traffic_wards}"
)

print(
    f"Traffic = Emission: "
    f"{traffic_wards == emission_wards}"
)

print(
    f"Emission = Policy: "
    f"{emission_wards == policy_wards}"
)


if not all_equal:

    raise ValueError(
        "Cross-dataset ward mismatch detected"
    )


print(
    "Cross-dataset consistency PASSED"
)


# =========================================================
# Final Validation Summary
# =========================================================

print(
    "\n" + "=" * 55
)

print(
    "FINAL PHASE 2 VALIDATION SUMMARY"
)

print(
    "=" * 55
)

print(
    f"Expected wards: {EXPECTED_WARDS}"
)

print(
    f"Population wards: "
    f"{len(population_wards)}"
)

print(
    f"LULC wards: "
    f"{len(lulc_wards)}"
)

print(
    f"LST wards: "
    f"{len(lst_wards)}"
)

print(
    f"Traffic wards: "
    f"{len(traffic_wards)}"
)

print(
    f"Emission wards: "
    f"{len(emission_wards)}"
)

print(
    f"Policy wards: "
    f"{len(policy_wards)}"
)


# =========================================================
# Final Pass
# =========================================================

if (
    len(population_wards) == EXPECTED_WARDS
    and
    len(lulc_wards) == EXPECTED_WARDS
    and
    len(lst_wards) == EXPECTED_WARDS
    and
    len(traffic_wards) == EXPECTED_WARDS
    and
    len(emission_wards) == EXPECTED_WARDS
    and
    len(policy_wards) == EXPECTED_WARDS
    and
    all_equal
):

    print(
        "\nALL PHASE 2 DATASETS "
        "VALIDATED SUCCESSFULLY"
    )

else:

    raise ValueError(
        "Final Phase 2 validation failed"
    )


print(
    "\nPhase 2 data foundation is ready "
    "for unified dataset creation."
)

print(
    "=" * 55
)