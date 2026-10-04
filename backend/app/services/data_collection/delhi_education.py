import os
import osmnx as ox


def collect_education_data():
    print("Collecting Delhi education facilities from OpenStreetMap...")

    tags = {
        "amenity": ["school", "college", "university", "kindergarten"]
    }

    education = ox.features_from_place(
        "Delhi, India",
        tags=tags
    )

    if education.empty:
        print("No education facilities found.")
        return

    output_dir = "data/raw/gis"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(
        output_dir,
        "delhi_education.geojson"
    )

    education = education.reset_index()

    education.to_file(
        output_file,
        driver="GeoJSON"
    )

    print(f"Education facilities collected: {len(education)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    collect_education_data()