import os
import geopandas as gpd


def create_traffic_features():
    print("Creating traffic-related features from Delhi road network...")

    input_file = "data/raw/gis/delhi_road_network.geojson"

    if not os.path.exists(input_file):
        print("Road network file not found.")
        return

    roads = gpd.read_file(input_file)

    print(f"Road segments loaded: {len(roads)}")

    # Calculate road length in meters
    roads_projected = roads.to_crs(epsg=32643)

    roads["road_length_m"] = roads_projected.geometry.length

    # Keep useful road attributes
    useful_columns = [
        "osmid",
        "highway",
        "name",
        "maxspeed",
        "lanes",
        "oneway",
        "road_length_m",
        "geometry"
    ]

    available_columns = [
        col for col in useful_columns
        if col in roads.columns
    ]

    traffic_features = roads[available_columns].copy()

    output_dir = "data/processed/gis"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(
        output_dir,
        "delhi_traffic_features.geojson"
    )

    traffic_features.to_file(
        output_file,
        driver="GeoJSON"
    )

    print(f"Traffic features created: {len(traffic_features)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    create_traffic_features()