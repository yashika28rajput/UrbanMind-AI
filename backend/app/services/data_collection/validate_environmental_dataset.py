from pathlib import Path

import pandas as pd


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "delhi_environmental_dataset.csv"
)


# =========================================================
# VALIDATION FUNCTION
# =========================================================

def validate_environmental_dataset():

    print()
    print("=" * 70)
    print("URBANMIND AI - ENVIRONMENTAL DATASET VALIDATION")
    print("=" * 70)

    # =====================================================
    # 1. CHECK FILE
    # =====================================================

    if not DATA_FILE.exists():

        print()
        print("ERROR: Environmental dataset not found.")
        print()
        print(DATA_FILE)

        return

    print()
    print("[1/8] File found")
    print(DATA_FILE)

    # =====================================================
    # 2. LOAD DATA
    # =====================================================

    df = pd.read_csv(DATA_FILE)

    print()
    print("[2/8] Data loaded successfully")

    # =====================================================
    # 3. DATASET SIZE
    # =====================================================

    rows, columns = df.shape

    print()
    print("[3/8] Dataset size")
    print(f"Rows    : {rows}")
    print(f"Columns : {columns}")

    # =====================================================
    # 4. REQUIRED WEATHER COLUMNS
    # =====================================================

    required_weather_columns = [
        "timestamp_local",
        "temperature_c",
        "relative_humidity_percent",
        "precipitation_mm",
        "surface_pressure_hpa",
        "wind_speed_kmh",
        "wind_direction_degrees"
    ]

    missing_weather_columns = [
        column
        for column in required_weather_columns
        if column not in df.columns
    ]

    print()
    print("[4/8] Weather columns")

    if missing_weather_columns:

        print("MISSING WEATHER COLUMNS:")

        for column in missing_weather_columns:
            print(f"  - {column}")

    else:

        print("All required weather columns are present.")

    # =====================================================
    # 5. POLLUTANT COLUMNS
    # =====================================================

    print()
    print("[5/8] Pollutant columns")

    excluded_columns = {
        "timestamp_local",
        "station_name",
        "city",
        "latitude",
        "longitude",
        "temperature_c",
        "relative_humidity_percent",
        "precipitation_mm",
        "surface_pressure_hpa",
        "wind_speed_kmh",
        "wind_direction_degrees"
    }

    pollutant_columns = [
        column
        for column in df.columns
        if column not in excluded_columns
    ]

    if pollutant_columns:

        print("Pollutant columns found:")

        for column in pollutant_columns:
            print(f"  - {column}")

    else:

        print("WARNING: No pollutant columns found.")

    # =====================================================
    # 6. MISSING VALUES
    # =====================================================

    print()
    print("[6/8] Missing values")

    missing_values = df.isnull().sum()

    print(
        missing_values.to_string()
    )

    # =====================================================
    # 7. DUPLICATES + TIMESTAMPS
    # =====================================================

    print()
    print("[7/8] Duplicate and timestamp validation")

    duplicate_count = df.duplicated().sum()

    print(
        f"Duplicate rows: {duplicate_count}"
    )

    if "timestamp_local" in df.columns:

        timestamps = pd.to_datetime(
            df["timestamp_local"],
            errors="coerce"
        )

        invalid_timestamps = timestamps.isna().sum()

        print(
            f"Invalid timestamps: "
            f"{invalid_timestamps}"
        )

        if invalid_timestamps == 0:

            print(
                f"First timestamp: "
                f"{timestamps.min()}"
            )

            print(
                f"Last timestamp: "
                f"{timestamps.max()}"
            )

    # =====================================================
    # 8. WEATHER COVERAGE
    # =====================================================

    print()
    print("[8/8] Weather coverage")

    if "temperature_c" in df.columns:

        temperature_missing = (
            df["temperature_c"]
            .isna()
            .sum()
        )

        print(
            f"Missing temperature values: "
            f"{temperature_missing}"
        )

    if "relative_humidity_percent" in df.columns:

        humidity_missing = (
            df["relative_humidity_percent"]
            .isna()
            .sum()
        )

        print(
            f"Missing humidity values: "
            f"{humidity_missing}"
        )

    # =====================================================
    # FINAL VALIDATION
    # =====================================================

    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    validation_passed = True

    # Dataset

    if rows > 0:

        print("Dataset contains records")

    else:

        validation_passed = False

        print("Dataset is empty")

    # Weather columns

    if missing_weather_columns:

        validation_passed = False

        print("Weather columns check FAILED")

    else:

        print("Weather columns check PASSED")

    # Timestamp

    if "timestamp_local" in df.columns:

        timestamps = pd.to_datetime(
            df["timestamp_local"],
            errors="coerce"
        )

        if timestamps.isna().sum() == 0:

            print("Timestamp validation PASSED")

        else:

            validation_passed = False

            print("Timestamp validation FAILED")

    # Pollutants

    if pollutant_columns:

        print("Pollutant data detected")

    else:

        validation_passed = False

        print("Pollutant data check FAILED")

    print()

    if validation_passed:

        print(
            "ENVIRONMENTAL DATASET VALIDATION PASSED"
        )

        print()
        print(
            "Step 8.5 is complete."
        )

    else:

        print(
            "ENVIRONMENTAL DATASET VALIDATION NEEDS ATTENTION"
        )

    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    validate_environmental_dataset()