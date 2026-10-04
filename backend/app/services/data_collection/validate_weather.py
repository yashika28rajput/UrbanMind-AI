from pathlib import Path

import pandas as pd


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "weather"
    / "delhi_weather.csv"
)


# =========================================================
# VALIDATION FUNCTION
# =========================================================

def validate_weather_data():

    print()
    print("=" * 70)
    print("URBANMIND AI - WEATHER DATA VALIDATION")
    print("=" * 70)

    # -----------------------------------------------------
    # 1. Check file
    # -----------------------------------------------------

    if not DATA_FILE.exists():

        print()
        print("ERROR: Weather data file not found.")
        print()
        print("Expected file:")
        print(DATA_FILE)

        return

    print()
    print("[1/8] File found")
    print(DATA_FILE)

    # -----------------------------------------------------
    # 2. Load data
    # -----------------------------------------------------

    df = pd.read_csv(DATA_FILE)

    print()
    print("[2/8] Data loaded successfully")

    # -----------------------------------------------------
    # 3. Dataset size
    # -----------------------------------------------------

    rows, columns = df.shape

    print()
    print("[3/8] Dataset size")
    print(f"Rows    : {rows}")
    print(f"Columns : {columns}")

    # -----------------------------------------------------
    # 4. Required columns
    # -----------------------------------------------------

    required_columns = [
        "city",
        "timestamp_local",
        "temperature_c",
        "relative_humidity_percent",
        "precipitation_mm",
        "surface_pressure_hpa",
        "wind_speed_kmh",
        "wind_direction_degrees",
        "latitude",
        "longitude"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    print()
    print("[4/8] Required columns")

    if missing_columns:

        print("MISSING COLUMNS:")

        for column in missing_columns:
            print(f"  - {column}")

    else:

        print("All required columns are present.")

    # -----------------------------------------------------
    # 5. Missing values
    # -----------------------------------------------------

    print()
    print("[5/8] Missing values")

    missing_values = df.isnull().sum()

    print(
        missing_values.to_string()
    )

    # -----------------------------------------------------
    # 6. Duplicate records
    # -----------------------------------------------------

    duplicate_count = df.duplicated().sum()

    print()
    print("[6/8] Duplicate records")
    print(f"Duplicates: {duplicate_count}")

    # -----------------------------------------------------
    # 7. Numeric validation
    # -----------------------------------------------------

    print()
    print("[7/8] Numeric data validation")

    numeric_columns = [
        "temperature_c",
        "relative_humidity_percent",
        "precipitation_mm",
        "surface_pressure_hpa",
        "wind_speed_kmh",
        "wind_direction_degrees",
        "latitude",
        "longitude"
    ]

    numeric_validation_passed = True

    for column in numeric_columns:

        if column in df.columns:

            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce"
            )

            invalid_values = numeric_values.isna().sum()

            if invalid_values > 0:

                numeric_validation_passed = False

                print(
                    f"{column}: "
                    f"{invalid_values} invalid values"
                )

            else:

                print(
                    f"{column}: valid"
                )

    # -----------------------------------------------------
    # 8. Geographic + temporal validation
    # -----------------------------------------------------

    print()
    print("[8/8] Geographic and temporal validation")

    geographic_validation_passed = True
    temporal_validation_passed = True

    if (
        "latitude" in df.columns
        and "longitude" in df.columns
    ):

        invalid_coordinates = (
            (df["latitude"] < -90)
            | (df["latitude"] > 90)
            | (df["longitude"] < -180)
            | (df["longitude"] > 180)
        ).sum()

        if invalid_coordinates > 0:

            geographic_validation_passed = False

            print(
                f"Invalid coordinates: "
                f"{invalid_coordinates}"
            )

        else:

            print("Geographic coordinates valid.")

    if "timestamp_local" in df.columns:

        timestamps = pd.to_datetime(
            df["timestamp_local"],
            errors="coerce"
        )

        invalid_timestamps = timestamps.isna().sum()

        if invalid_timestamps > 0:

            temporal_validation_passed = False

            print(
                f"Invalid timestamps: "
                f"{invalid_timestamps}"
            )

        else:

            print("Timestamps valid.")

            print(
                f"First timestamp: "
                f"{timestamps.min()}"
            )

            print(
                f"Last timestamp: "
                f"{timestamps.max()}"
            )

    # =====================================================
    # FINAL VALIDATION STATUS
    # =====================================================

    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    validation_passed = True

    # Required columns

    if missing_columns:

        validation_passed = False

        print("Required columns check FAILED")

    else:

        print("Required columns check PASSED")

    # Empty dataset

    if rows == 0:

        validation_passed = False

        print("Dataset is empty")

    else:

        print("Dataset contains records")

    # Numeric values

    if numeric_validation_passed:

        print("Numeric data validation PASSED")

    else:

        validation_passed = False

        print("Numeric data validation FAILED")

    # Geographic validation

    if geographic_validation_passed:

        print("Geographic validation PASSED")

    else:

        validation_passed = False

        print("Geographic validation FAILED")

    # Temporal validation

    if temporal_validation_passed:

        print("Temporal validation PASSED")

    else:

        validation_passed = False

        print("Temporal validation FAILED")

    print()

    if validation_passed:

        print("WEATHER DATA VALIDATION PASSED")

        print()
        print("Step 8.3 is complete.")

    else:

        print("WEATHER DATA VALIDATION NEEDS ATTENTION")

    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    validate_weather_data()