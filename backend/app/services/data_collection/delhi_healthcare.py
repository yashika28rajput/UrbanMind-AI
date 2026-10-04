from pathlib import Path

import geopandas as gpd
import osmnx as ox


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "gis"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "delhi_healthcare.geojson"
)


# =========================================================
# SETTINGS
# =========================================================

PLACE_NAME = "Delhi, India"


# =========================================================
# MAIN FUNCTION
# =========================================================

def collect_delhi_healthcare():

    print()
    print("=" * 70)
    print("URBANMIND AI - DELHI HEALTHCARE DATA ACQUISITION")
    print("=" * 70)

    # -----------------------------------------------------
    # 1. Output directory
    # -----------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("[1/5] Output directory ready")

    # -----------------------------------------------------
    # 2. Download healthcare facilities
    # -----------------------------------------------------

    print()
    print("[2/5] Downloading healthcare facilities from OpenStreetMap")
    print("This may take some time...")

    tags = {
        "amenity": [
            "hospital",
            "clinic",
            "doctors",
            "pharmacy"
        ]
    }

    try:

        healthcare = ox.features.features_from_place(
            PLACE_NAME,
            tags=tags
        )

    except Exception as error:

        print()
        print("ERROR: Could not download healthcare data.")
        print(error)

        return

    # -----------------------------------------------------
    # 3. Check data
    # -----------------------------------------------------

    print()
    print("[3/5] Healthcare data downloaded")

    if healthcare.empty:

        print()
        print("WARNING: No healthcare facilities found.")

        return

    # -----------------------------------------------------
    # 4. Prepare GeoDataFrame
    # -----------------------------------------------------

    print()
    print("[4/5] Preparing healthcare geospatial data")

    healthcare = healthcare.reset_index()

    preferred_columns = [
        "element_type",
        "osmid",
        "name",
        "amenity",
        "healthcare",
        "operator",
        "emergency",
        "phone",
        "website",
        "addr:street",
        "addr:city",
        "geometry"
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in healthcare.columns
    ]

    healthcare = healthcare[
        available_columns
    ]

    # Ensure WGS84

    if healthcare.crs is not None:

        healthcare = healthcare.to_crs(
            epsg=4326
        )

    # -----------------------------------------------------
    # 5. Save GeoJSON
    # -----------------------------------------------------

    print()
    print("[5/5] Saving healthcare dataset")

    healthcare.to_file(
        OUTPUT_FILE,
        driver="GeoJSON"
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("DELHI HEALTHCARE DATA ACQUISITION COMPLETE")
    print("=" * 70)

    print()
    print(f"Healthcare facilities : {len(healthcare)}")
    print(f"Columns               : {len(healthcare.columns)}")

    print()
    print("Output file:")
    print(OUTPUT_FILE)

    print()
    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    collect_delhi_healthcare()