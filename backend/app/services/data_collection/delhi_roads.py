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
    / "delhi_road_network.geojson"
)


# =========================================================
# SETTINGS
# =========================================================

PLACE_NAME = "Delhi, India"

NETWORK_TYPE = "drive"


# =========================================================
# MAIN FUNCTION
# =========================================================

def collect_delhi_roads():

    print()
    print("=" * 70)
    print("URBANMIND AI - DELHI ROAD NETWORK ACQUISITION")
    print("=" * 70)

    # -----------------------------------------------------
    # 1. Create output directory
    # -----------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("[1/5] Output directory ready")
    print(OUTPUT_DIR)

    # -----------------------------------------------------
    # 2. Download road network
    # -----------------------------------------------------

    print()
    print("[2/5] Downloading Delhi road network from OpenStreetMap")
    print("This may take some time...")

    try:

        graph = ox.graph.graph_from_place(
            PLACE_NAME,
            network_type=NETWORK_TYPE,
            simplify=True
        )

    except Exception as error:

        print()
        print("ERROR: Could not download road network.")
        print(error)

        return

    # -----------------------------------------------------
    # 3. Convert graph to GeoDataFrames
    # -----------------------------------------------------

    print()
    print("[3/5] Converting road network to GeoDataFrame")

    nodes, edges = ox.graph_to_gdfs(
        graph
    )

    # -----------------------------------------------------
    # 4. Prepare road data
    # -----------------------------------------------------

    print()
    print("[4/5] Preparing road network")

    edges = edges.reset_index()

    # Keep only useful columns when available

    preferred_columns = [
        "osmid",
        "name",
        "highway",
        "oneway",
        "lanes",
        "maxspeed",
        "length",
        "geometry"
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in edges.columns
    ]

    edges = edges[
        available_columns
    ]

    # Ensure WGS84 coordinate system

    if edges.crs is not None:

        edges = edges.to_crs(
            epsg=4326
        )

    # -----------------------------------------------------
    # 5. Save GeoJSON
    # -----------------------------------------------------

    print()
    print("[5/5] Saving road network")

    edges.to_file(
        OUTPUT_FILE,
        driver="GeoJSON"
    )

    # -----------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("DELHI ROAD NETWORK ACQUISITION COMPLETE")
    print("=" * 70)

    print()
    print(f"Road segments : {len(edges)}")
    print(f"Columns       : {len(edges.columns)}")

    print()
    print("Output file:")
    print(OUTPUT_FILE)

    print()
    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    collect_delhi_roads()