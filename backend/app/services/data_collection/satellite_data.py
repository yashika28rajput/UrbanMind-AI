import ee


# ============================================================
# UrbanMind AI - Satellite Data Pipeline
# ============================================================

PROJECT_ID = "urbanmind-ai-508808"

START_DATE = "2026-07-01"
END_DATE = "2026-08-01"

MAX_CLOUD_PERCENTAGE = 20
EXPORT_SCALE = 10

DRIVE_FOLDER = "UrbanMindAI_Satellite"


# ============================================================
# 1. INITIALIZE GOOGLE EARTH ENGINE
# ============================================================

def initialize_gee():
    ee.Initialize(project=PROJECT_ID)
    print("GEE initialized successfully")


# ============================================================
# 2. GET DELHI REGION OF INTEREST
# ============================================================

def get_delhi_roi():

    delhi = ee.FeatureCollection(
        "FAO/GAUL/2015/level1"
    )

    delhi = delhi.filter(
        ee.Filter.eq("ADM0_NAME", "India")
    )

    delhi = delhi.filter(
        ee.Filter.eq("ADM1_NAME", "Delhi")
    )

    roi = delhi.geometry()

    print("Delhi ROI loaded successfully")

    area_km2 = roi.area().divide(1000000).getInfo()

    print("Area (km2):", area_km2)

    return roi


# ============================================================
# 3. SENTINEL-2 CLOUD MASKING
# ============================================================

def mask_s2_clouds(image):

    qa = image.select("QA60")

    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11

    cloud_mask = qa.bitwiseAnd(cloud_bit).eq(0)

    cirrus_mask = qa.bitwiseAnd(cirrus_bit).eq(0)

    mask = cloud_mask.And(cirrus_mask)

    return image.updateMask(mask)


# ============================================================
# 4. CREATE SENTINEL-2 MEDIAN COMPOSITE
# ============================================================

def create_sentinel2_composite(roi):

    collection = ee.ImageCollection(
        "COPERNICUS/S2_SR_HARMONIZED"
    )

    collection = collection.filterBounds(roi)

    collection = collection.filterDate(
        START_DATE,
        END_DATE
    )

    collection = collection.filter(
        ee.Filter.lt(
            "CLOUDY_PIXEL_PERCENTAGE",
            MAX_CLOUD_PERCENTAGE
        )
    )

    collection = collection.map(
        mask_s2_clouds
    )

    image_count = collection.size().getInfo()

    print(
        "Images after cloud filtering:",
        image_count
    )

    if image_count == 0:
        raise RuntimeError(
            "No Sentinel-2 images found."
        )

    composite = collection.median()

    composite = composite.clip(roi)

    print(
        "Sentinel-2 median composite "
        "created successfully"
    )

    bands = composite.bandNames().getInfo()

    print("Available bands:")

    print(bands)

    return composite


# ============================================================
# 5. CALCULATE NDVI AND NDBI
# ============================================================

def calculate_satellite_indices(composite):

    print("")
    print("Calculating satellite indices...")

    # --------------------------------------------------------
    # NDVI
    #
    # Formula:
    # (NIR - Red) / (NIR + Red)
    #
    # Sentinel-2:
    # B8 = NIR
    # B4 = Red
    # --------------------------------------------------------

    ndvi = composite.normalizedDifference(
        ["B8", "B4"]
    )

    ndvi = ndvi.rename("NDVI")

    # --------------------------------------------------------
    # NDBI
    #
    # Formula:
    # (SWIR - NIR) / (SWIR + NIR)
    #
    # Sentinel-2:
    # B11 = SWIR
    # B8 = NIR
    # --------------------------------------------------------

    ndbi = composite.normalizedDifference(
        ["B11", "B8"]
    )

    ndbi = ndbi.rename("NDBI")

    # Combine NDVI and NDBI
    indices = ndvi.addBands(ndbi)

    print(
        "NDVI and NDBI calculated successfully"
    )

    print("Index bands:")

    print(
        indices.bandNames().getInfo()
    )

    # --------------------------------------------------------
    # NDVI RANGE
    # --------------------------------------------------------

    ndvi_stats = ndvi.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=composite.geometry(),
        scale=100,
        maxPixels=1000000000
    )

    ndvi_stats = ndvi_stats.getInfo()

    print(
        "NDVI range:",
        ndvi_stats
    )

    # --------------------------------------------------------
    # NDBI RANGE
    # --------------------------------------------------------

    ndbi_stats = ndbi.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=composite.geometry(),
        scale=100,
        maxPixels=1000000000
    )

    ndbi_stats = ndbi_stats.getInfo()

    print(
        "NDBI range:",
        ndbi_stats
    )

    return indices


# ============================================================
# 6. EXPORT NDVI + NDBI TO GOOGLE DRIVE
# ============================================================

def export_satellite_indices(indices, roi):

    print("")
    print(
        "Starting satellite indices export..."
    )

    task = ee.batch.Export.image.toDrive(
        image=indices,
        description="UrbanMindAI_Satellite_Indices",
        folder=DRIVE_FOLDER,
        fileNamePrefix="delhi_satellite_indices",
        region=roi,
        scale=EXPORT_SCALE,
        maxPixels=10000000000,
        fileFormat="GeoTIFF"
    )

    task.start()

    print(
        "Export task started successfully"
    )

    print(
        "Google Drive folder:",
        DRIVE_FOLDER
    )

    print(
        "File name:",
        "delhi_satellite_indices.tif"
    )

    print(
        "Bands:",
        "NDVI, NDBI"
    )


# ============================================================
# 7. CHECK EARTH ENGINE TASKS
# ============================================================

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


# ============================================================
# 8. MAIN PIPELINE
# ============================================================

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "UrbanMind AI - Satellite Data Pipeline"
    )

    print(
        "=========================================="
    )

    # Step 1
    initialize_gee()

    # Step 2
    roi = get_delhi_roi()

    # Step 3
    composite = create_sentinel2_composite(
        roi
    )

    # Step 4
    indices = calculate_satellite_indices(
        composite
    )

    # Step 5
    export_satellite_indices(
        indices,
        roi
    )

    # Step 6
    check_export_tasks()

    print(
        "=========================================="
    )

    print(
        "Satellite processing completed"
    )

    print(
        "NDVI + NDBI export submitted"
    )

    print(
        "=========================================="
    )