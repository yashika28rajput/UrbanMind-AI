import geopandas as gpd
import pandas as pd


POPULATION_FILE = (
    "data/processed/population/"
    "delhi_population_ward_gis.geojson"
)

LULC_FILE = (
    "data/processed/satellite/"
    "delhi_ward_lulc.csv"
)

OUTPUT_FILE = (
    "data/processed/urban/"
    "delhi_ward_population_lulc.geojson"
)


def load_population_data():
    print("")
    print("Loading population and ward GIS data...")

    population = gpd.read_file(
        POPULATION_FILE
    )

    print(
        "Population GIS records:",
        len(population)
    )

    return population


def load_lulc_data():
    print("")
    print("Loading ward-level LULC data...")

    lulc = pd.read_csv(
        LULC_FILE
    )

    print(
        "LULC records:",
        len(lulc)
    )

    return lulc


def normalize_ward_numbers(
    population,
    lulc
):
    print("")
    print("Normalizing Ward_No...")

    population["Ward_No"] = pd.to_numeric(
        population["Ward_No"],
        errors="coerce"
    ).astype("Int64")

    lulc["Ward_No"] = pd.to_numeric(
        lulc["Ward_No"],
        errors="coerce"
    ).astype("Int64")

    return population, lulc


def validate_ward_matching(
    population,
    lulc
):
    print("")
    print("Validating ward matching...")

    population_wards = set(
        population["Ward_No"].dropna()
    )

    lulc_wards = set(
        lulc["Ward_No"].dropna()
    )

    common = population_wards.intersection(
        lulc_wards
    )

    population_only = (
        population_wards - lulc_wards
    )

    lulc_only = (
        lulc_wards - population_wards
    )

    print(
        "Common wards:",
        len(common)
    )

    print(
        "Population-only wards:",
        len(population_only)
    )

    print(
        "LULC-only wards:",
        len(lulc_only)
    )

    if len(common) != 272:
        raise ValueError(
            "Ward matching failed."
        )

    if len(population_only) != 0:
        raise ValueError(
            "Population-only wards found."
        )

    if len(lulc_only) != 0:
        raise ValueError(
            "LULC-only wards found."
        )

    print(
        "Ward matching validation passed"
    )


def merge_population_lulc(
    population,
    lulc
):
    print("")
    print("Merging population and LULC data...")

    lulc_columns = [
        "Ward_No",
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
        "water_surface",
    ]

    lulc_subset = lulc[
        lulc_columns
    ].copy()

    merged = population.merge(
        lulc_subset,
        on="Ward_No",
        how="left",
        validate="one_to_one"
    )

    print(
        "Merged records:",
        len(merged)
    )

    return merged


def validate_merged_dataset(
    merged
):
    print("")
    print("Validating merged dataset...")

    required_lulc_columns = [
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
        "water_surface",
    ]

    print(
        "Records:",
        len(merged)
    )

    print(
        "Unique wards:",
        merged["Ward_No"].nunique()
    )

    print(
        "Duplicate wards:",
        merged["Ward_No"].duplicated().sum()
    )

    missing_values = (
        merged[required_lulc_columns]
        .isna()
        .sum()
        .sum()
    )

    print(
        "Missing LULC values:",
        int(missing_values)
    )

    for column in required_lulc_columns:

        if not pd.api.types.is_numeric_dtype(
            merged[column]
        ):
            raise ValueError(
                f"LULC column is not numeric: {column}"
            )

    if len(merged) != 272:
        raise ValueError(
            "Merged dataset must contain 272 wards."
        )

    if merged["Ward_No"].duplicated().sum() != 0:
        raise ValueError(
            "Duplicate Ward_No found."
        )

    if missing_values != 0:
        raise ValueError(
            "Missing LULC values found."
        )

    print(
        "Merged dataset validation passed"
    )


def save_dataset(
    merged
):
    print("")
    print("Saving integrated urban dataset...")

    merged.to_file(
        OUTPUT_FILE,
        driver="GeoJSON"
    )

    print(
        "Saved:",
        OUTPUT_FILE
    )


def print_summary(
    merged
):
    print("")
    print("==========================================")
    print("Population + LULC Summary")
    print("==========================================")

    print(
        "Wards:",
        len(merged)
    )

    if "TOT_P" in merged.columns:

        total_population = pd.to_numeric(
            merged["TOT_P"],
            errors="coerce"
        ).sum()

        print(
            "Total population:",
            int(total_population)
        )

    print(
        "Average built fraction:",
        round(
            merged["built"].mean(),
            4
        )
    )

    print(
        "Average vegetation fraction:",
        round(
            merged["vegetation"].mean(),
            4
        )
    )

    print(
        "Average water fraction:",
        round(
            merged["water"].mean(),
            4
        )
    )

    print(
        "Average bare-land fraction:",
        round(
            merged["bare"].mean(),
            4
        )
    )


if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "UrbanMind AI - Population + LULC Integration"
    )

    print(
        "=========================================="
    )

    population = load_population_data()

    lulc = load_lulc_data()

    population, lulc = normalize_ward_numbers(
        population,
        lulc
    )

    validate_ward_matching(
        population,
        lulc
    )

    merged = merge_population_lulc(
        population,
        lulc
    )

    validate_merged_dataset(
        merged
    )

    save_dataset(
        merged
    )

    print_summary(
        merged
    )

    print(
        "=========================================="
    )

    print(
        "Population + LULC integration completed"
    )

    print(
        "=========================================="
    )