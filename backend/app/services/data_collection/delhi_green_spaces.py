import os
import osmnx as ox


def collect_green_spaces():
    print("Collecting Delhi green spaces from OpenStreetMap...")

    tags = {
        "leisure": [
            "park",
            "garden",
            "nature_reserve",
            "recreation_ground"
        ]
    }

    green_spaces = ox.features_from_place(
        "Delhi, India",
        tags=tags
    )

    if green_spaces.empty:
        print("No green spaces found.")
        return

    output_dir = "data/raw/gis"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(
        output_dir,
        "delhi_green_spaces.geojson"
    )

    green_spaces = green_spaces.reset_index()

    green_spaces.to_file(
        output_file,
        driver="GeoJSON"
    )

    print(f"Green spaces collected: {len(green_spaces)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    collect_green_spaces()