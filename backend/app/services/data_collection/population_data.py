import os
import pandas as pd
import geopandas as gpd


def create_population_gis_dataset():

    print("Creating Delhi ward population GIS dataset...")

    input_file = "data/raw/population/2011-IndiaStateDistSbDistTwnWrd-0000.xlsx"
    gis_file = "data/raw/gis/Delhi_Wards.geojson"

    if not os.path.exists(input_file):
        print("Population Excel file not found.")
        return

    if not os.path.exists(gis_file):
        print("Delhi ward GIS file not found.")
        return

    # -----------------------------
    # 1. Read Census population data
    # -----------------------------

    df = pd.read_excel(
        input_file,
        sheet_name="Data"
    )

    # Delhi = State code 7
    delhi = df[
        df["State"].astype(str).str.strip() == "7"
    ].copy()

    # Keep records having ward numbers
    delhi = delhi[
        delhi["Ward"].astype(str).str.strip() != "0"
    ].copy()

    # Convert Ward to numeric
    delhi["Ward"] = pd.to_numeric(
        delhi["Ward"],
        errors="coerce"
    )

    delhi = delhi.dropna(subset=["Ward"])

    delhi["Ward"] = delhi["Ward"].astype(int)

    # -----------------------------
    # 2. Aggregate multiple Census
    #    records belonging to a ward
    # -----------------------------

    numeric_columns = [
        "No_HH",
        "TOT_P",
        "TOT_M",
        "TOT_F",
        "P_06",
        "P_LIT",
        "P_ILL"
    ]

    for column in numeric_columns:
        delhi[column] = pd.to_numeric(
            delhi[column],
            errors="coerce"
        ).fillna(0)

    population = (
        delhi
        .groupby("Ward", as_index=False)[numeric_columns]
        .sum()
    )

    # -----------------------------
    # 3. Read Delhi ward GIS
    # -----------------------------

    wards = gpd.read_file(gis_file)

    wards["Ward_No_numeric"] = pd.to_numeric(
        wards["Ward_No"],
        errors="coerce"
    )

    wards = wards.dropna(
        subset=["Ward_No_numeric"]
    )

    wards["Ward_No_numeric"] = (
        wards["Ward_No_numeric"]
        .astype(int)
    )

    # -----------------------------
    # 4. Merge population + geometry
    # -----------------------------

    merged = wards.merge(
        population,
        left_on="Ward_No_numeric",
        right_on="Ward",
        how="left"
    )

    merged = merged.drop(
        columns=["Ward_No_numeric"]
    )

    # -----------------------------
    # 5. Save final GeoJSON
    # -----------------------------

    output_dir = "data/processed/population"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    output_file = os.path.join(
        output_dir,
        "delhi_population_ward_gis.geojson"
    )

    merged.to_file(
        output_file,
        driver="GeoJSON"
    )

    # -----------------------------
    # 6. Validation
    # -----------------------------

    print("\n=== POPULATION GIS DATASET ===")
    print("GIS wards:", len(wards))
    print("Aggregated population wards:", len(population))
    print("Final merged records:", len(merged))

    print(
        "Unique Ward_No:",
        merged["Ward_No"].nunique()
    )

    print(
        "Duplicate Ward_No:",
        merged["Ward_No"].duplicated().sum()
    )

    print(
        "Missing population:",
        merged["TOT_P"].isna().sum()
    )

    print(
        "Total population:",
        int(merged["TOT_P"].sum())
    )

    print(
        "Total households:",
        int(merged["No_HH"].sum())
    )

    print(
        "\nSaved to:",
        output_file
    )


if __name__ == "__main__":
    create_population_gis_dataset()