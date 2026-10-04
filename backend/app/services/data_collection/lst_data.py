import ee
import geopandas as gpd
import pandas as pd


PROJECT_ID = "urbanmind-ai-508808"

START_DATE = "2026-07-01"
END_DATE = "2026-08-01"

WARD_GEOJSON = "data/raw/gis/Delhi_Wards.geojson"

DRIVE_FOLDER = "UrbanMindAI_LST"

EXPORT_DESCRIPTION = "UrbanMindAI_Ward_LST"
EXPORT_FILENAME = "delhi_ward_lst"

EXPORT_SCALE = 30


def initialize_gee():
    print("")
    print("Initializing Google Earth Engine...")

    ee.Initialize(project=PROJECT_ID)

    print("GEE initialized successfully")


def get_delhi_roi():
    print("")
    print("Loading Delhi ROI...")

    delhi = ee.FeatureCollection(
        "FAO/GAUL/2015/level1"
    )

    delhi = delhi.filter(
        ee.Filter.eq(
            "ADM0_NAME",
            "India"
        )
    )

    delhi = delhi.filter(
        ee.Filter.eq(
            "ADM1_NAME",
            "Delhi"
        )
    )

    roi = delhi.geometry()

    area_km2 = (
        roi.area()
        .divide(1000000)
        .getInfo()
    )

    print(
        "Delhi ROI loaded successfully"
    )

    print(
        "Delhi area (km2):",
        area_km2
    )

    return roi


def load_ward_boundaries():
    print("")
    print("Loading Delhi ward boundaries...")

    gdf = gpd.read_file(
        WARD_GEOJSON
    )

    print(
        "Total GIS records:",
        len(gdf)
    )

    ward_numbers = pd.to_numeric(
        gdf["Ward_No"],
        errors="coerce"
    )

    gdf = gdf[
        ward_numbers.notna()
    ].copy()

    gdf["Ward_No"] = ward_numbers[
        ward_numbers.notna()
    ].astype(int)

    gdf = gdf[
        [
            "Ward_No",
            "Ward_Name",
            "geometry"
        ]
    ]

    gdf = gdf.drop_duplicates(
        subset=["Ward_No"]
    )

    gdf = gdf[
        gdf.geometry.notna()
    ]

    print(
        "Numeric ward records:",
        len(gdf)
    )

    print(
        "Unique wards:",
        gdf["Ward_No"].nunique()
    )

    features = []

    for _, row in gdf.iterrows():

        geometry = ee.Geometry(
            row.geometry.__geo_interface__
        )

        feature = ee.Feature(
            geometry,
            {
                "Ward_No": int(
                    row["Ward_No"]
                ),
                "Ward_Name": str(
                    row["Ward_Name"]
                )
            }
        )

        features.append(
            feature
        )

    wards = ee.FeatureCollection(
        features
    )

    print(
        "Earth Engine ward FeatureCollection created"
    )

    return wards


def create_landsat_collection(
    roi
):
    print("")
    print("Loading Landsat 9 data...")

    collection = ee.ImageCollection(
        "LANDSAT/LC09/C02/T1_L2"
    )

    collection = collection.filterBounds(
        roi
    )

    collection = collection.filterDate(
        START_DATE,
        END_DATE
    )

    image_count = collection.size().getInfo()

    print(
        "Landsat 9 images found:",
        image_count
    )

    if image_count == 0:

        raise RuntimeError(
            "No Landsat 9 images found."
        )

    return collection


def mask_landsat_clouds(
    image
):
    qa_pixel = image.select(
        "QA_PIXEL"
    )

    cloud_shadow = 1 << 4
    cloud = 1 << 3
    cirrus = 1 << 2

    mask = (
        qa_pixel
        .bitwiseAnd(cloud_shadow)
        .eq(0)
        .And(
            qa_pixel
            .bitwiseAnd(cloud)
            .eq(0)
        )
        .And(
            qa_pixel
            .bitwiseAnd(cirrus)
            .eq(0)
        )
    )

    return image.updateMask(
        mask
    )


def calculate_lst(
    collection,
    roi
):
    print("")
    print("Calculating Land Surface Temperature...")

    collection = collection.map(
        mask_landsat_clouds
    )

    thermal = collection.select(
        "ST_B10"
    ).median()

    thermal = thermal.clip(
        roi
    )

    # Landsat Collection 2 Level-2
    # surface temperature scale factor
    # and offset.
    lst_kelvin = (
        thermal
        .multiply(0.00341802)
        .add(149.0)
        .rename("LST_K")
    )

    lst_celsius = (
        lst_kelvin
        .subtract(273.15)
        .rename("LST_C")
    )

    print(
        "LST calculation completed"
    )

    print(
        "Output bands:",
        lst_celsius.bandNames().getInfo()
    )

    stats = lst_celsius.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=roi,
        scale=100,
        maxPixels=1000000000
    )

    print(
        "LST range (Celsius):",
        stats.getInfo()
    )

    return lst_celsius


def calculate_ward_lst(
    lst_image,
    wards
):
    print("")
    print(
        "Calculating ward-level mean LST..."
    )

    ward_lst = lst_image.reduceRegions(
        collection=wards,
        reducer=ee.Reducer.mean(),
        scale=EXPORT_SCALE,
        tileScale=4
    )

    print(
        "Ward-level LST statistics generated"
    )

    return ward_lst


def rename_lst_property(
    feature
):
    return feature.set(
        "mean_LST_C",
        feature.get("mean")
    ).select(
        [
            "Ward_No",
            "Ward_Name",
            "mean_LST_C"
        ]
    )


def prepare_export_collection(
    ward_lst
):
    print("")
    print(
        "Preparing final LST dataset..."
    )

    ward_lst = ward_lst.map(
        rename_lst_property
    )

    return ward_lst


def export_ward_lst(
    ward_lst
):
    print("")
    print(
        "Starting ward-level LST export..."
    )

    task = ee.batch.Export.table.toDrive(
        collection=ward_lst,

        description=EXPORT_DESCRIPTION,

        folder=DRIVE_FOLDER,

        fileNamePrefix=EXPORT_FILENAME,

        fileFormat="CSV",

        selectors=[
            "Ward_No",
            "Ward_Name",
            "mean_LST_C"
        ]
    )

    task.start()

    print(
        "LST export task started successfully"
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
    print(
        "Checking Earth Engine tasks..."
    )

    tasks = ee.batch.Task.list()

    if len(tasks) == 0:

        print(
            "No Earth Engine tasks found."
        )

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
        "UrbanMind AI - LST Data Pipeline"
    )

    print(
        "=========================================="
    )

    initialize_gee()

    roi = get_delhi_roi()

    wards = load_ward_boundaries()

    collection = create_landsat_collection(
        roi
    )

    lst_image = calculate_lst(
        collection,
        roi
    )

    ward_lst = calculate_ward_lst(
        lst_image,
        wards
    )

    ward_lst = prepare_export_collection(
        ward_lst
    )

    export_ward_lst(
        ward_lst
    )

    check_export_tasks()

    print(
        "=========================================="
    )

    print(
        "LST processing submitted"
    )

    print(
        "Ward-level LST CSV export started"
    )

    print(
        "=========================================="
    )