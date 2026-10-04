import os
import math
import pandas as pd
import geopandas as gpd


# ================================================================
# UrbanMind AI - Ward Health Impact / Exposure Layer
# ================================================================

print("=" * 70)
print("UrbanMind AI - Ward Health Impact / Exposure Layer")
print("=" * 70)


# ----------------------------------------------------------------
# Paths
# ----------------------------------------------------------------

POPULATION_FILE = (
    "data/processed/population/delhi_ward_population.csv"
)

ENVIRONMENT_FILE = (
    "data/processed/ml/environmental/"
    "delhi_ward_environmental_risk.csv"
)

WARD_GEOMETRY_FILE = (
    "data/raw/gis/Delhi_Wards.geojson"
)

OUTPUT_DIR = "data/processed/ml/health"

OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_health_impact.csv"
)

OUTPUT_GEOJSON = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_health_impact.geojson"
)

OUTPUT_SUMMARY = os.path.join(
    OUTPUT_DIR,
    "health_impact_summary.json"
)


# ----------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------

def check_file(path, name):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )

    print(f"{name}: FOUND")


def normalize_ward_ids(df, column):
    df = df.copy()

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    invalid = df[column].isna().sum()

    if invalid > 0:
        raise ValueError(
            f"Invalid Ward_No values found in {column}: {invalid}"
        )

    df[column] = df[column].astype(int)

    return df


def check_infinite_values(df, columns):
    for column in columns:
        values = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        infinite_count = sum(
            not pd.isna(value) and not math.isfinite(float(value))
            for value in values
        )

        print(
            f"{column}: {infinite_count}"
        )

        if infinite_count > 0:
            raise ValueError(
                f"Infinite values found in {column}"
            )


# ----------------------------------------------------------------
# Start
# ----------------------------------------------------------------

print("\nChecking required files...")

check_file(
    POPULATION_FILE,
    "Ward population"
)

check_file(
    ENVIRONMENT_FILE,
    "Environmental risk layer"
)

check_file(
    WARD_GEOMETRY_FILE,
    "Ward geometry"
)


# ----------------------------------------------------------------
# Load population
# ----------------------------------------------------------------

print("\nLoading ward population...")

population = pd.read_csv(
    POPULATION_FILE
)

print(
    f"Population records: {len(population)}"
)

required_population_columns = [
    "Ward_No",
    "No_HH",
    "TOT_P",
    "TOT_M",
    "TOT_F",
    "P_06",
    "P_LIT",
    "P_ILL",
    "children_percent",
    "literacy_percent",
    "illiteracy_percent"
]

missing = [
    column
    for column in required_population_columns
    if column not in population.columns
]

if missing:
    raise ValueError(
        f"Missing population columns: {missing}"
    )

print("Population column validation: PASSED")


# ----------------------------------------------------------------
# Load environmental risk
# ----------------------------------------------------------------

print("\nLoading environmental risk data...")

environment = pd.read_csv(
    ENVIRONMENT_FILE
)

print(
    f"Environmental records: {len(environment)}"
)

required_environment_columns = [
    "Ward_No",
    "Ward_Name",
    "final_AQI",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score",
    "environmental_risk_category",
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C"
]

missing = [
    column
    for column in required_environment_columns
    if column not in environment.columns
]

if missing:
    raise ValueError(
        f"Missing environmental columns: {missing}"
    )

print("Environmental column validation: PASSED")


# ----------------------------------------------------------------
# Normalize Ward IDs
# ----------------------------------------------------------------

print("\nNormalizing Ward IDs...")

population = normalize_ward_ids(
    population,
    "Ward_No"
)

environment = normalize_ward_ids(
    environment,
    "Ward_No"
)

print("Ward ID normalization: PASSED")


# ----------------------------------------------------------------
# Duplicate validation
# ----------------------------------------------------------------

print("\nChecking duplicate wards...")

population_duplicates = (
    population["Ward_No"].duplicated().sum()
)

environment_duplicates = (
    environment["Ward_No"].duplicated().sum()
)

print(
    f"Population duplicates: {population_duplicates}"
)

print(
    f"Environmental duplicates: {environment_duplicates}"
)

if population_duplicates > 0:
    raise ValueError(
        "Duplicate Ward_No found in population data."
    )

if environment_duplicates > 0:
    raise ValueError(
        "Duplicate Ward_No found in environmental data."
    )

print("Duplicate validation: PASSED")


# ----------------------------------------------------------------
# Ward coverage
# ----------------------------------------------------------------

print("\nChecking ward coverage...")

population_wards = set(
    population["Ward_No"]
)

environment_wards = set(
    environment["Ward_No"]
)

population_only = (
    population_wards - environment_wards
)

environment_only = (
    environment_wards - population_wards
)

print(
    f"Population-only wards: {len(population_only)}"
)

print(
    f"Environment-only wards: {len(environment_only)}"
)

if population_only or environment_only:
    raise ValueError(
        "Population and environmental ward coverage do not match."
    )

print(
    f"Common wards: {len(population_wards)}"
)

print("Ward coverage validation: PASSED")


# ----------------------------------------------------------------
# Merge
# ----------------------------------------------------------------

print("\nMerging population and environmental data...")

health = population.merge(
    environment,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"Records after merge: {len(health)}"
)

if len(health) != len(population):
    raise ValueError(
        "Unexpected records lost during merge."
    )

print("Population + environment merge: PASSED")


# ----------------------------------------------------------------
# Convert numeric columns
# ----------------------------------------------------------------

print("\nPreparing health exposure indicators...")

numeric_columns = [
    "TOT_P",
    "No_HH",
    "TOT_M",
    "TOT_F",
    "P_06",
    "P_LIT",
    "P_ILL",
    "children_percent",
    "literacy_percent",
    "illiteracy_percent",
    "final_AQI",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score",
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C"
]

for column in numeric_columns:
    health[column] = pd.to_numeric(
        health[column],
        errors="coerce"
    )


# ----------------------------------------------------------------
# Missing-value validation
# ----------------------------------------------------------------

print("\nChecking missing values...")

missing_values = (
    health[numeric_columns]
    .isna()
    .sum()
)

print(
    missing_values[
        missing_values > 0
    ]
)

if missing_values.sum() > 0:
    raise ValueError(
        "Missing values found in health indicators."
    )

print("Missing-value validation: PASSED")


# ----------------------------------------------------------------
# Infinite-value validation
# ----------------------------------------------------------------

print("\nChecking infinite values...")

check_infinite_values(
    health,
    numeric_columns
)

print("Infinite-value validation: PASSED")


# ================================================================
# HEALTH EXPOSURE INDICATORS
# ================================================================

print("\nCreating population exposure indicators...")


# ----------------------------------------------------------------
# AQI exposure
# ----------------------------------------------------------------

health["population_AQI_exposure"] = (
    health["TOT_P"]
    * health["AQI_risk_index"]
)


# ----------------------------------------------------------------
# Heat exposure
# ----------------------------------------------------------------

health["population_heat_exposure"] = (
    health["TOT_P"]
    * health["heat_risk_index"]
)


# ----------------------------------------------------------------
# Environmental exposure
# ----------------------------------------------------------------

health["population_environmental_exposure"] = (
    health["TOT_P"]
    * health["environmental_risk_score"]
)


# ----------------------------------------------------------------
# Child vulnerability
# ----------------------------------------------------------------

health["child_vulnerability_population"] = (
    health["P_06"]
    * health["heat_risk_index"]
)


# ----------------------------------------------------------------
# Combined population vulnerability
# ----------------------------------------------------------------

health["population_vulnerability_index"] = (
    0.30 * health["AQI_risk_index"]
    + 0.30 * health["heat_risk_index"]
    + 0.20 * health["environmental_risk_score"]
    + 0.20 * (
        health["children_percent"] / 100
    )
)


# ----------------------------------------------------------------
# Population health exposure score
# ----------------------------------------------------------------

health["health_exposure_score"] = (
    health["population_vulnerability_index"]
    * 100
)


# ----------------------------------------------------------------
# Population-weighted environmental burden
# ----------------------------------------------------------------

health["population_weighted_environmental_burden"] = (
    health["environmental_risk_score"]
    * health["TOT_P"]
)


# ================================================================
# HEALTH EXPOSURE CATEGORY
# ================================================================

print("\nCreating health exposure categories...")


def exposure_category(score):
    if score < 20:
        return "Low"

    if score < 40:
        return "Moderate"

    if score < 60:
        return "High"

    return "Very High"


health["health_exposure_category"] = (
    health["health_exposure_score"]
    .apply(exposure_category)
)


# ================================================================
# FINAL VALIDATION
# ================================================================

print("\nValidating health exposure layer...")

health_indicator_columns = [
    "population_AQI_exposure",
    "population_heat_exposure",
    "population_environmental_exposure",
    "child_vulnerability_population",
    "population_vulnerability_index",
    "health_exposure_score",
    "population_weighted_environmental_burden"
]

check_infinite_values(
    health,
    health_indicator_columns
)

if health[health_indicator_columns].isna().any().any():
    raise ValueError(
        "Missing values found in final health indicators."
    )

print("Health indicator validation: PASSED")


# ----------------------------------------------------------------
# Load geometry
# ----------------------------------------------------------------

print("\nLoading ward geometry...")

wards = gpd.read_file(
    WARD_GEOMETRY_FILE
)

print(
    f"Ward geometry records: {len(wards)}"
)

print(
    f"Ward CRS: {wards.crs}"
)


# ----------------------------------------------------------------
# Normalize geometry Ward IDs
# ----------------------------------------------------------------

print("\nPreparing ward geometry...")

wards["Ward_No_numeric"] = pd.to_numeric(
    wards["Ward_No"],
    errors="coerce"
)

invalid_geometry_wards = (
    wards["Ward_No_numeric"].isna()
)

print(
    "Non-numeric geometry records removed:",
    invalid_geometry_wards.sum()
)

wards = wards[
    ~invalid_geometry_wards
].copy()

wards["Ward_No"] = (
    wards["Ward_No_numeric"]
    .astype(int)
)

wards = wards.drop(
    columns=["Ward_No_numeric"]
)


# ----------------------------------------------------------------
# Keep only required ward geometry
# ----------------------------------------------------------------

wards = wards[
    ["Ward_No", "geometry"]
].copy()

wards = wards.drop_duplicates(
    subset=["Ward_No"]
)

print(
    f"Numeric ward geometry records: {len(wards)}"
)


# ----------------------------------------------------------------
# Geometry coverage
# ----------------------------------------------------------------

health_wards = set(
    health["Ward_No"]
)

geometry_wards = set(
    wards["Ward_No"]
)

missing_geometry = (
    health_wards - geometry_wards
)

if missing_geometry:
    raise ValueError(
        f"Missing geometry for wards: "
        f"{sorted(missing_geometry)}"
    )

print("Geometry coverage: PASSED")


# ----------------------------------------------------------------
# Attach geometry
# ----------------------------------------------------------------

print("\nAttaching ward geometry...")

health_geo = wards.merge(
    health,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"Health geometry records: {len(health_geo)}"
)


# ----------------------------------------------------------------
# Geometry validation
# ----------------------------------------------------------------

missing_geometry_count = (
    health_geo.geometry.isna().sum()
)

invalid_geometry_count = (
    (~health_geo.geometry.is_valid).sum()
)

print(
    f"Missing geometry: {missing_geometry_count}"
)

print(
    f"Invalid geometry: {invalid_geometry_count}"
)

if missing_geometry_count > 0:
    raise ValueError(
        "Missing geometry found."
    )

if invalid_geometry_count > 0:
    raise ValueError(
        "Invalid geometry found."
    )

print("Geometry validation: PASSED")


# ----------------------------------------------------------------
# Set CRS
# ----------------------------------------------------------------

if health_geo.crs is None:
    health_geo = health_geo.set_crs(
        "EPSG:4326"
    )
else:
    health_geo = health_geo.to_crs(
        "EPSG:4326"
    )


# ================================================================
# SAVE CSV
# ================================================================

print("\nSaving health impact CSV...")

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

health_csv = health_geo.drop(
    columns="geometry"
)

health_csv.to_csv(
    OUTPUT_CSV,
    index=False
)

print(
    f"CSV saved:\n{OUTPUT_CSV}"
)


# ================================================================
# SAVE GEOJSON
# ================================================================

print("\nSaving health impact GeoJSON...")

health_geo.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)

print(
    f"GeoJSON saved:\n{OUTPUT_GEOJSON}"
)


# ================================================================
# SUMMARY
# ================================================================

print("\nCreating summary...")

summary = {
    "wards": int(len(health_geo)),
    "total_population": int(
        health["TOT_P"].sum()
    ),
    "total_children_0_6": int(
        health["P_06"].sum()
    ),
    "mean_AQI": float(
        health["final_AQI"].mean()
    ),
    "mean_environmental_risk": float(
        health["environmental_risk_score"].mean()
    ),
    "mean_health_exposure_score": float(
        health["health_exposure_score"].mean()
    ),
    "health_exposure_distribution": {
        str(key): int(value)
        for key, value in
        health[
            "health_exposure_category"
        ]
        .value_counts()
        .to_dict()
        .items()
    }
}

import json

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


# ================================================================
# FINAL VALIDATION
# ================================================================

print("\n" + "=" * 70)
print("FINAL HEALTH IMPACT VALIDATION")
print("=" * 70)

print(
    f"272 wards: {len(health_geo) == 272}"
)

print(
    f"Population available: "
    f"{health['TOT_P'].notna().all()}"
)

print(
    f"AQI available: "
    f"{health['final_AQI'].notna().all()}"
)

print(
    f"Heat risk available: "
    f"{health['heat_risk_index'].notna().all()}"
)

print(
    f"Environmental risk available: "
    f"{health['environmental_risk_score'].notna().all()}"
)

print(
    f"Health exposure score available: "
    f"{health['health_exposure_score'].notna().all()}"
)

print(
    f"No missing indicators: "
    f"{not health[health_indicator_columns].isna().any().any()}"
)

print(
    f"Geometry available: "
    f"{health_geo.geometry.notna().all()}"
)

print(
    f"Geometry valid: "
    f"{health_geo.geometry.is_valid.all()}"
)

print(
    f"CSV exists: "
    f"{os.path.exists(OUTPUT_CSV)}"
)

print(
    f"GeoJSON exists: "
    f"{os.path.exists(OUTPUT_GEOJSON)}"
)

print(
    f"Summary exists: "
    f"{os.path.exists(OUTPUT_SUMMARY)}"
)


# ================================================================
# SUMMARY
# ================================================================

print("\n" + "=" * 70)
print("WARD HEALTH EXPOSURE SUMMARY")
print("=" * 70)

print(
    f"Wards: {len(health_geo)}"
)

print(
    f"Population: "
    f"{health['TOT_P'].sum():,.0f}"
)

print(
    f"Children (0-6): "
    f"{health['P_06'].sum():,.0f}"
)

print(
    f"Mean AQI: "
    f"{health['final_AQI'].mean():.2f}"
)

print(
    f"Mean environmental risk: "
    f"{health['environmental_risk_score'].mean():.3f}"
)

print(
    f"Mean health exposure score: "
    f"{health['health_exposure_score'].mean():.2f}"
)

print("\nHealth exposure distribution:")

print(
    health[
        "health_exposure_category"
    ].value_counts()
)

print("\nOutput files:")

print(OUTPUT_CSV)
print(OUTPUT_GEOJSON)
print(OUTPUT_SUMMARY)

print("\n" + "=" * 70)
print("WARD HEALTH IMPACT / EXPOSURE LAYER COMPLETED")
print("=" * 70)