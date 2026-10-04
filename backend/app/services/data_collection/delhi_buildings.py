import os
import osmnx as ox


def collect_buildings():
    print("Collecting Delhi building footprints from OpenStreetMap...")

    tags = {
        "building": True
    }

    buildings = ox.features_from_place(
        "Delhi, India",
        tags=tags
    )

    if buildings.empty:
        print("No buildings found.")
        return

    output_dir = "data/raw/gis"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(
        output_dir,
        "delhi_buildings.geojson"
    )

    buildings = buildings.reset_index()

    buildings.to_file(
        output_file,
        driver="GeoJSON"
    )

    print(f"Buildings collected: {len(buildings)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    collect_buildings()