import json
import ee
import geopandas as gpd
import pandas as pd


PROJECT_ID = "urbanmind-ai-508808"

START_DATE = "2026-07-01"
END_DATE = "2026-08-01"

WARD_GEOJSON = "data/raw/gis/Delhi_Wards.geojson"

DRIVE_FOLDER = "UrbanMindAI_LULC"

EXPORT_DESCRIPTION = "UrbanMindAI_Ward_LULC"
EXPORT_FILENAME = "delhi_ward_lulc"

EXPORT_SCALE = 10


LULC_CLASSES = {
    0: "water",
    1: "trees",
    2: "grass",
    3: "flooded_vegetation",
    4: "crops",
    5: "shrub_and_scrub",
    6: "built",
    7: "bare",
    8: "snow_and_ice",
}


def initialize_gee():
    print("")
    print("Initializing Google Earth Engine...")

    ee.Initialize(project=PROJECT_ID)

    print("GEE initialized successfully")


def get_delhi_roi():
    print("")
    print("Loading Delhi ROI...")

    delhi = ee.FeatureCollection("FAO/GAUL/2015/level1")

    delhi = delhi.filter(
        ee.Filter.eq("ADM0_NAME", "India")
    )

    delhi = delhi.filter(
        ee.Filter.eq("ADM1_NAME", "Delhi")
    )

    roi = delhi.geometry()

    area_km2 = (
        roi.area()
        .divide(1000000)
        .getInfo()
    )

    print("Delhi ROI loaded successfully")
    print("Delhi area (km2):", area_km2)

    return roi


def load_ward_boundaries():
    print("")
    print("Loading Delhi ward boundaries...")

    gdf = gpd.read_file(WARD_GEOJSON)

    print("Total GIS records:", len(gdf))

    numeric_wards = pd.to_numeric(
        gdf["Ward_No"],
        errors="coerce"
    )

    gdf = gdf[numeric_wards.notna()].copy()

    gdf["Ward_No"] = numeric_wards[
        numeric_wards.notna()
    ].astype(int)

    gdf = gdf[
        ["Ward_No", "Ward_Name", "geometry"]
    ]

    gdf = gdf.drop_duplicates(
        subset=["Ward_No"]
    )

    gdf = gdf[
        gdf.geometry.notna()
    ]

    print("Numeric ward records:", len(gdf))
    print("Unique wards:", gdf["Ward_No"].nunique())

    features = []

    for _, row in gdf.iterrows():

        geometry_json = row.geometry.__geo_interface__

        geometry = ee.Geometry(
            geometry_json
        )

        feature = ee.Feature(
            geometry,
            {
                "Ward_No": int(row["Ward_No"]),
                "Ward_Name": str(row["Ward_Name"]),
            }
        )

        features.append(feature)

    wards = ee.FeatureCollection(features)

    print("Earth Engine ward FeatureCollection created")

    return wards


def create_dynamic_world_composite(roi):
    print("")
    print("Loading Dynamic World LULC data...")

    collection = ee.ImageCollection(
        "GOOGLE/DYNAMICWORLD/V1"
    )

    collection = collection.filterBounds(roi)

    collection = collection.filterDate(
        START_DATE,
        END_DATE
    )

    image_count = collection.size().getInfo()

    print(
        "Dynamic World images found:",
        image_count
    )

    if image_count == 0:
        raise RuntimeError(
            "No Dynamic World images found for the selected period."
        )

    print("Creating LULC composite...")

    label_composite = collection.select(
        "label"
    ).mode()

    label_composite = label_composite.clip(
        roi
    )

    print(
        "Dynamic World LULC composite created successfully"
    )

    return label_composite


def create_lulc_fraction_image(label_image):
    print("")
    print("Creating LULC class fraction layers...")

    fraction_image = None

    for class_id, class_name in LULC_CLASSES.items():

        class_fraction = (
            label_image
            .eq(class_id)
            .rename(class_name)
        )

        if fraction_image is None:
            fraction_image = class_fraction
        else:
            fraction_image = fraction_image.addBands(
                class_fraction
            )

    print("LULC fraction bands:")

    print(
        fraction_image.bandNames().getInfo()
    )

    return fraction_image


def calculate_ward_lulc(wards, fraction_image):
    print("")
    print("Calculating ward-level LULC percentages...")

    ward_lulc = fraction_image.reduceRegions(
        collection=wards,
        reducer=ee.Reducer.mean(),
        scale=EXPORT_SCALE,
        tileScale=4
    )

    print(
        "Ward-level LULC statistics generated"
    )

    return ward_lulc


def add_lulc_summary(feature):
    built = ee.Number(
        feature.get("built")
    )

    trees = ee.Number(
        feature.get("trees")
    )

    grass = ee.Number(
        feature.get("grass")
    )

    water = ee.Number(
        feature.get("water")
    )

    vegetation = (
        trees
        .add(grass)
    )

    return (
        feature
        .set(
            "vegetation",
            vegetation
        )
        .set(
            "built_environment",
            built
        )
        .set(
            "water_surface",
            water
        )
    )


def prepare_export_collection(ward_lulc):
    print("")
    print("Preparing final LULC dataset...")

    ward_lulc = ward_lulc.map(
        add_lulc_summary
    )

    selectors = [
        "Ward_No",
        "Ward_Name",
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

    return ward_lulc, selectors


def export_ward_lulc(
    ward_lulc,
    selectors
):
    print("")
    print("Starting ward-level LULC export...")

    task = ee.batch.Export.table.toDrive(
        collection=ward_lulc,

        description=EXPORT_DESCRIPTION,

        folder=DRIVE_FOLDER,

        fileNamePrefix=EXPORT_FILENAME,

        fileFormat="CSV",

        selectors=selectors
    )

    task.start()

    print(
        "LULC export task started successfully"
    )

    print(
        "Google Drive folder:",
        DRIVE_FOLDER
    )

    print(
        "File:",
        EXPORT_FILENAME + ".csv"
    )


def check_export_tasks():
    print("")
    print("Checking Earth Engine tasks...")

    tasks = ee.batch.Task.list()

    if len(tasks) == 0:
        print("No Earth Engine tasks found.")
        return

    for task in tasks[:10]:

        status = task.status()

        print(
            "Task:",
            status.get("description")
        )

        print(
            "State:",
            status.get("state")
        )

        error_message = status.get(
            "error_message"
        )

        if error_message:
            print(
                "Error:",
                error_message
            )

        print(
            "------------------------------"
        )


if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "UrbanMind AI - LULC Data Pipeline"
    )

    print(
        "=========================================="
    )

    initialize_gee()

    roi = get_delhi_roi()

    wards = load_ward_boundaries()

    label_image = create_dynamic_world_composite(
        roi
    )

    fraction_image = create_lulc_fraction_image(
        label_image
    )

    ward_lulc = calculate_ward_lulc(
        wards,
        fraction_image
    )

    ward_lulc, selectors = prepare_export_collection(
        ward_lulc
    )

    export_ward_lulc(
        ward_lulc,
        selectors
    )

    check_export_tasks()

    print(
        "=========================================="
    )

    print(
        "LULC processing submitted"
    )

    print(
        "Ward-level LULC CSV export started"
    )

    print(
        "=========================================="
    )