import os
import numpy as np
import pandas as pd
import geopandas as gpd


print("=" * 45)
print("UrbanMind AI - Policy Planning Features")
print("=" * 45)


# =========================================================
# Paths
# =========================================================

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

OUTPUT_DIR = (
    "data/processed/policy"
)

OUTPUT_PATH = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_policy_planning_features.geojson"
)


# =========================================================
# Helper Function
# =========================================================

def normalize_ward_id(df):
    """
    Convert Ward_No to integer format.
    """

    df = df.copy()

    df["Ward_No"] = pd.to_numeric(
        df["Ward_No"],
        errors="coerce"
    )

    df = df[
        df["Ward_No"].notna()
    ].copy()

    df["Ward_No"] = (
        df["Ward_No"]
        .astype(np.int64)
    )

    return df


def min_max_normalize(series):
    """
    Normalize values between 0 and 1.
    """

    minimum = series.min()
    maximum = series.max()

    if (
        pd.isna(minimum)
        or
        pd.isna(maximum)
        or
        maximum == minimum
    ):

        return pd.Series(
            np.zeros(len(series)),
            index=series.index
        )

    return (
        (series - minimum)
        /
        (maximum - minimum)
    )


# =========================================================
# Load Population
# =========================================================

print("\nLoading population data...")

population_gdf = gpd.read_file(
    POPULATION_PATH
)

print(
    f"Population records: "
    f"{len(population_gdf)}"
)


# =========================================================
# Load LULC
# =========================================================

print("\nLoading LULC data...")

lulc = pd.read_csv(
    LULC_PATH
)

print(
    f"LULC records: "
    f"{len(lulc)}"
)


# =========================================================
# Load LST
# =========================================================

print("\nLoading LST data...")

lst = pd.read_csv(
    LST_PATH
)

print(
    f"LST records: "
    f"{len(lst)}"
)


# =========================================================
# Load Traffic
# =========================================================

print("\nLoading traffic data...")

traffic = gpd.read_file(
    TRAFFIC_PATH
)

print(
    f"Traffic records: "
    f"{len(traffic)}"
)


# =========================================================
# Load Emission Features
# =========================================================

print("\nLoading emission features...")

emission = gpd.read_file(
    EMISSION_PATH
)

print(
    f"Emission records: "
    f"{len(emission)}"
)


# =========================================================
# Normalize Ward IDs
# =========================================================

print("\nNormalizing ward IDs...")

population_gdf = normalize_ward_id(
    population_gdf
)

lulc = normalize_ward_id(
    lulc
)

lst = normalize_ward_id(
    lst
)

traffic = normalize_ward_id(
    traffic
)

emission = normalize_ward_id(
    emission
)


# =========================================================
# Remove Duplicate Wards
# =========================================================

population_gdf = (
    population_gdf
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)

lulc = (
    lulc
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)

lst = (
    lst
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)

traffic = (
    traffic
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)

emission = (
    emission
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)


# =========================================================
# Population Attributes
# =========================================================

population_columns = [
    "Ward_No",
    "TOT_P",
    "No_HH"
]

for column in population_columns:

    if column not in population_gdf.columns:

        raise KeyError(
            f"Missing population column: "
            f"{column}"
        )

population = pd.DataFrame(
    population_gdf[
        population_columns
    ].copy()
)

population["Ward_No"] = (
    population["Ward_No"]
    .astype(np.int64)
)

population["TOT_P"] = pd.to_numeric(
    population["TOT_P"],
    errors="coerce"
)

population["No_HH"] = pd.to_numeric(
    population["No_HH"],
    errors="coerce"
)


# =========================================================
# LULC Attributes
# =========================================================

lulc_columns = [
    "Ward_No",
    "trees",
    "grass",
    "crops",
    "shrub_and_scrub",
    "built",
    "bare",
    "vegetation",
    "built_environment",
    "water_surface"
]

for column in lulc_columns:

    if column not in lulc.columns:

        raise KeyError(
            f"Missing LULC column: "
            f"{column}"
        )

lulc = lulc[
    lulc_columns
].copy()

for column in lulc_columns[1:]:

    lulc[column] = pd.to_numeric(
        lulc[column],
        errors="coerce"
    )


# =========================================================
# LST Attributes
# =========================================================

if "mean_LST_C" not in lst.columns:

    raise KeyError(
        "mean_LST_C not found in LST dataset"
    )

lst = lst[
    [
        "Ward_No",
        "mean_LST_C"
    ]
].copy()

lst["mean_LST_C"] = pd.to_numeric(
    lst["mean_LST_C"],
    errors="coerce"
)


# =========================================================
# Traffic Attributes
# =========================================================

traffic_columns = [
    "Ward_No",
    "total_road_length_km",
    "major_road_length_km",
    "oneway_fraction"
]

for column in traffic_columns:

    if column not in traffic.columns:

        raise KeyError(
            f"Missing traffic column: "
            f"{column}"
        )

traffic = traffic[
    traffic_columns
].copy()

for column in traffic_columns[1:]:

    traffic[column] = pd.to_numeric(
        traffic[column],
        errors="coerce"
    )


# =========================================================
# Emission Attributes
# =========================================================

emission_columns = [
    "Ward_No",
    "emission_pressure_index",
    "traffic_pressure_index",
    "built_pressure_index",
    "heat_pressure_index",
    "vegetation_mitigation_index"
]

for column in emission_columns:

    if column not in emission.columns:

        raise KeyError(
            f"Missing emission column: "
            f"{column}"
        )

emission = emission[
    emission_columns
].copy()

for column in emission_columns[1:]:

    emission[column] = pd.to_numeric(
        emission[column],
        errors="coerce"
    )


# =========================================================
# Merge Population + LULC
# =========================================================

print("\nMerging population and LULC...")

policy = population.merge(
    lulc,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After Population + LULC: "
    f"{len(policy)} wards"
)


# =========================================================
# Merge LST
# =========================================================

print("\nMerging LST...")

policy = policy.merge(
    lst,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After LST: "
    f"{len(policy)} wards"
)


# =========================================================
# Merge Traffic
# =========================================================

print("\nMerging traffic...")

policy = policy.merge(
    traffic,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After traffic: "
    f"{len(policy)} wards"
)


# =========================================================
# Merge Emission
# =========================================================

print("\nMerging emission features...")

policy = policy.merge(
    emission,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After emission: "
    f"{len(policy)} wards"
)


# =========================================================
# Ward Area
# =========================================================

print("\nCalculating ward area...")

ward_geometry = (
    population_gdf[
        [
            "Ward_No",
            "geometry"
        ]
    ].copy()
)

ward_geometry["Ward_No"] = (
    ward_geometry["Ward_No"]
    .astype(np.int64)
)

projected_geometry = (
    ward_geometry
    .to_crs("EPSG:32644")
)

projected_geometry[
    "ward_area_km2"
] = (
    projected_geometry.geometry.area
    /
    1_000_000
)

ward_area = pd.DataFrame(
    projected_geometry[
        [
            "Ward_No",
            "ward_area_km2"
        ]
    ]
)

policy = policy.merge(
    ward_area,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)


# =========================================================
# Population Density
# =========================================================

print("\nCalculating planning indicators...")

policy[
    "population_density_per_km2"
] = (
    policy["TOT_P"]
    /
    policy["ward_area_km2"].replace(
        0,
        np.nan
    )
)


# =========================================================
# Green Cover Potential
# =========================================================

# Higher potential where population density is high
# and vegetation availability is comparatively low.

policy[
    "green_cover_intervention_potential"
] = (
    min_max_normalize(
        policy["population_density_per_km2"]
    )
    *
    (
        1 -
        policy["vegetation"]
    )
)


# =========================================================
# Urban Forest Potential
# =========================================================

policy[
    "urban_forest_potential"
] = (
    (
        1 -
        policy["vegetation"]
    )
    *
    policy["built_environment"]
    *
    min_max_normalize(
        policy["population_density_per_km2"]
    )
)


# =========================================================
# Roadside Greening Potential
# =========================================================

policy[
    "roadside_greening_potential"
] = (
    min_max_normalize(
        policy["major_road_length_km"]
    )
    *
    (
        1 -
        policy["vegetation"]
    )
)


# =========================================================
# Cool Roof Potential
# =========================================================

policy[
    "cool_roof_intervention_potential"
] = (
    policy["built_environment"]
    *
    min_max_normalize(
        policy["mean_LST_C"]
    )
)


# =========================================================
# Water Restoration Potential
# =========================================================

policy[
    "water_body_restoration_potential"
] = (
    (
        1 -
        policy["water_surface"]
    )
    *
    min_max_normalize(
        policy["mean_LST_C"]
    )
)


# =========================================================
# Heat Mitigation Potential
# =========================================================

policy[
    "heat_mitigation_potential"
] = (
    min_max_normalize(
        policy["mean_LST_C"]
    )
    *
    (
        1 -
        policy["vegetation"]
    )
)


# =========================================================
# Air Pollution Mitigation Potential
# =========================================================

policy[
    "air_pollution_mitigation_potential"
] = (
    policy[
        "emission_pressure_index"
    ]
    *
    (
        1 -
        policy["vegetation"]
    )
)


# =========================================================
# Sustainable Mobility Potential
# =========================================================

policy[
    "sustainable_mobility_potential"
] = (
    policy[
        "traffic_pressure_index"
    ]
    *
    (
        1 -
        policy[
            "oneway_fraction"
        ]
    )
)


# =========================================================
# Combined Planning Priority
# =========================================================

policy[
    "urban_intervention_potential"
] = (
    0.25
    *
    policy[
        "green_cover_intervention_potential"
    ]
    +
    0.20
    *
    policy[
        "cool_roof_intervention_potential"
    ]
    +
    0.20
    *
    policy[
        "air_pollution_mitigation_potential"
    ]
    +
    0.15
    *
    policy[
        "roadside_greening_potential"
    ]
    +
    0.10
    *
    policy[
        "urban_forest_potential"
    ]
    +
    0.10
    *
    policy[
        "sustainable_mobility_potential"
    ]
)


# =========================================================
# Clean Numeric Values
# =========================================================

numeric_columns = (
    policy
    .select_dtypes(
        include=[np.number]
    )
    .columns
)

policy[numeric_columns] = (
    policy[numeric_columns]
    .replace(
        [np.inf, -np.inf],
        np.nan
    )
)

policy[numeric_columns] = (
    policy[numeric_columns]
    .fillna(0)
)


# =========================================================
# Attach Geometry
# =========================================================

print("\nAttaching ward geometry...")

policy = ward_geometry.merge(
    policy,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

policy = gpd.GeoDataFrame(
    policy,
    geometry="geometry",
    crs=population_gdf.crs
)


# =========================================================
# Validation
# =========================================================

print(
    "\nValidating policy planning dataset..."
)

records = len(policy)

unique_wards = (
    policy["Ward_No"].nunique()
)

duplicate_wards = (
    policy["Ward_No"]
    .duplicated()
    .sum()
)

missing_geometry = (
    policy.geometry.isna()
    .sum()
)

invalid_geometry = (
    (~policy.geometry.is_valid)
    .sum()
)

missing_priority = (
    policy[
        "urban_intervention_potential"
    ].isna()
    .sum()
)

infinite_values = (
    np.isinf(
        policy.select_dtypes(
            include=[np.number]
        )
    )
    .sum()
    .sum()
)


print(
    f"Records: {records}"
)

print(
    f"Unique wards: {unique_wards}"
)

print(
    f"Duplicate wards: {duplicate_wards}"
)

print(
    f"Missing geometries: {missing_geometry}"
)

print(
    f"Invalid geometries: {invalid_geometry}"
)

print(
    "Missing intervention potential: "
    f"{missing_priority}"
)

print(
    "Infinite numeric values: "
    f"{infinite_values}"
)


# =========================================================
# Validation Checks
# =========================================================

if records != 272:

    raise ValueError(
        f"Expected 272 wards, "
        f"found {records}"
    )


if unique_wards != 272:

    raise ValueError(
        f"Expected 272 unique wards, "
        f"found {unique_wards}"
    )


if duplicate_wards != 0:

    raise ValueError(
        "Duplicate Ward_No values detected"
    )


if missing_geometry != 0:

    raise ValueError(
        "Missing ward geometries detected"
    )


if invalid_geometry != 0:

    raise ValueError(
        "Invalid ward geometries detected"
    )


if missing_priority != 0:

    raise ValueError(
        "Missing intervention "
        "potential detected"
    )


if infinite_values != 0:

    raise ValueError(
        "Infinite numeric values detected"
    )


print(
    "Policy planning validation passed"
)


# =========================================================
# Save
# =========================================================

print(
    "\nSaving policy planning features..."
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

policy.to_file(
    OUTPUT_PATH,
    driver="GeoJSON"
)

print(
    f"Saved: {OUTPUT_PATH}"
)


# =========================================================
# Summary
# =========================================================

print(
    "\n" + "=" * 45
)

print(
    "Ward-Level Policy Planning Summary"
)

print(
    "=" * 45
)

print(
    f"Wards: {len(policy)}"
)

print(
    "Average green-cover intervention "
    "potential: "
    f"{policy['green_cover_intervention_potential'].mean():.4f}"
)

print(
    "Average cool-roof intervention "
    "potential: "
    f"{policy['cool_roof_intervention_potential'].mean():.4f}"
)

print(
    "Average urban-forest potential: "
    f"{policy['urban_forest_potential'].mean():.4f}"
)

print(
    "Average roadside-greening potential: "
    f"{policy['roadside_greening_potential'].mean():.4f}"
)

print(
    "Average water-restoration potential: "
    f"{policy['water_body_restoration_potential'].mean():.4f}"
)

print(
    "Average heat-mitigation potential: "
    f"{policy['heat_mitigation_potential'].mean():.4f}"
)

print(
    "Average air-pollution mitigation "
    "potential: "
    f"{policy['air_pollution_mitigation_potential'].mean():.4f}"
)

print(
    "Average sustainable-mobility "
    "potential: "
    f"{policy['sustainable_mobility_potential'].mean():.4f}"
)

print(
    "Average urban intervention potential: "
    f"{policy['urban_intervention_potential'].mean():.4f}"
)

print(
    "=" * 45
)

print(
    "Policy planning feature extraction completed"
)

print(
    "=" * 45
)