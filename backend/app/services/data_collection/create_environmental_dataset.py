from pathlib import Path

import pandas as pd


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

AIR_QUALITY_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "air_quality"
    / "delhi_air_quality_measurements_july_2026.csv"
)

WEATHER_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "weather"
    / "delhi_weather.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "delhi_environmental_dataset.csv"
)


# =========================================================
# FUNCTION: NORMALIZE TIMESTAMP
# =========================================================

def normalize_timestamp(series):

    timestamps = pd.to_datetime(
        series,
        errors="coerce"
    )

    # If timestamps contain timezone information,
    # convert them to Delhi time and remove timezone.

    if timestamps.dt.tz is not None:

        timestamps = (
            timestamps
            .dt.tz_convert("Asia/Kolkata")
            .dt.tz_localize(None)
        )

    return timestamps


# =========================================================
# MAIN DATASET CREATION FUNCTION
# =========================================================

def create_environmental_dataset():

    print()
    print("=" * 70)
    print("URBANMIND AI - ENVIRONMENTAL DATASET CREATION")
    print("=" * 70)

    # =====================================================
    # 1. CHECK INPUT FILES
    # =====================================================

    print()
    print("[1/6] Checking input files")

    if not AIR_QUALITY_FILE.exists():

        print()
        print("ERROR: Air-quality file not found.")
        print(AIR_QUALITY_FILE)

        return

    if not WEATHER_FILE.exists():

        print()
        print("ERROR: Weather file not found.")
        print(WEATHER_FILE)

        return

    print("Air-quality file found.")
    print("Weather file found.")

    # =====================================================
    # 2. LOAD DATASETS
    # =====================================================

    print()
    print("[2/6] Loading datasets")

    try:

        air_quality = pd.read_csv(
            AIR_QUALITY_FILE
        )

        weather = pd.read_csv(
            WEATHER_FILE
        )

    except Exception as error:

        print()
        print("ERROR: Could not load datasets.")
        print(error)

        return

    print(
        f"Air-quality records : {len(air_quality)}"
    )

    print(
        f"Weather records     : {len(weather)}"
    )

    # =====================================================
    # 3. CHECK REQUIRED COLUMNS
    # =====================================================

    print()
    print("[3/6] Checking required columns")

    air_required_columns = [
        "timestamp_local",
        "parameter",
        "value"
    ]

    weather_required_columns = [
        "timestamp_local",
        "temperature_c",
        "relative_humidity_percent",
        "precipitation_mm",
        "surface_pressure_hpa",
        "wind_speed_kmh",
        "wind_direction_degrees"
    ]

    missing_air_columns = [
        column
        for column in air_required_columns
        if column not in air_quality.columns
    ]

    missing_weather_columns = [
        column
        for column in weather_required_columns
        if column not in weather.columns
    ]

    if missing_air_columns:

        print()
        print("ERROR: Missing air-quality columns:")

        for column in missing_air_columns:
            print(f"  - {column}")

        return

    if missing_weather_columns:

        print()
        print("ERROR: Missing weather columns:")

        for column in missing_weather_columns:
            print(f"  - {column}")

        return

    print("Required columns are present.")

    # =====================================================
    # 4. NORMALIZE TIMESTAMPS
    # =====================================================

    print()
    print("[4/6] Normalizing timestamps")

    air_quality["timestamp_local"] = normalize_timestamp(
        air_quality["timestamp_local"]
    )

    weather["timestamp_local"] = normalize_timestamp(
        weather["timestamp_local"]
    )

    # Remove invalid timestamps

    air_quality = air_quality.dropna(
        subset=["timestamp_local"]
    )

    weather = weather.dropna(
        subset=["timestamp_local"]
    )

    # =====================================================
    # 5. AGGREGATE + MERGE
    # =====================================================

    print()
    print("[5/6] Creating environmental dataset")

    # -----------------------------------------------------
    # Air-quality hourly aggregation
    # -----------------------------------------------------

    group_columns = [
        "timestamp_local",
        "parameter"
    ]

    if "station_name" in air_quality.columns:

        group_columns.insert(
            1,
            "station_name"
        )

    air_quality_hourly = (
        air_quality
        .groupby(
            group_columns,
            as_index=False
        )["value"]
        .mean()
    )

    # -----------------------------------------------------
    # Convert pollutant rows into columns
    # -----------------------------------------------------

    index_columns = [
        "timestamp_local"
    ]

    if "station_name" in air_quality_hourly.columns:

        index_columns.append(
            "station_name"
        )

    air_quality_pivot = (
        air_quality_hourly
        .pivot_table(
            index=index_columns,
            columns="parameter",
            values="value",
            aggfunc="mean"
        )
        .reset_index()
    )

    air_quality_pivot.columns.name = None

    # -----------------------------------------------------
    # Weather timestamp duplicates protection
    # -----------------------------------------------------

    weather = (
        weather
        .sort_values("timestamp_local")
        .drop_duplicates(
            subset=["timestamp_local"]
        )
    )

    # -----------------------------------------------------
    # Merge AQ + Weather
    # -----------------------------------------------------

    environmental_data = pd.merge(
        air_quality_pivot,
        weather,
        on="timestamp_local",
        how="left"
    )

    # =====================================================
    # SAVE PROCESSED DATASET
    # =====================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    environmental_data.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    print()
    print("Air-quality records loaded :",
          len(air_quality))

    print(
        "Weather records loaded     :",
        len(weather)
    )

    print(
        "Final environmental records:",
        len(environmental_data)
    )

    print(
        "Final columns              :",
        len(environmental_data.columns)
    )

    print()
    print("Output file:")
    print(OUTPUT_FILE)

    print()
    print("First 5 records:")

    print(
        environmental_data
        .head()
        .to_string(index=False)
    )

    print()
    print("=" * 70)
    print("ENVIRONMENTAL DATASET CREATION COMPLETE")
    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    create_environmental_dataset()