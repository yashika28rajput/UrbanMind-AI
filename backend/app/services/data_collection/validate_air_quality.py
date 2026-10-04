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
    / "air_quality"
    / "delhi_air_quality_measurements_july_2026.csv"
)


# =========================================================
# VALIDATION FUNCTION
# =========================================================

def validate_air_quality_data():

    print()
    print("=" * 70)
    print("URBANMIND AI - AIR QUALITY DATA VALIDATION")
    print("=" * 70)


    # -----------------------------------------------------
    # 1. Check file
    # -----------------------------------------------------

    if not DATA_FILE.exists():

        print()
        print("ERROR: Air-quality measurement file not found.")
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
        "location_id",
        "station_name",
        "sensor_id",
        "parameter",
        "value",
        "units",
        "timestamp_utc",
        "timestamp_local",
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
    # 7. Pollutants
    # -----------------------------------------------------

    print()
    print("[7/8] Pollutants found")

    if "parameter" in df.columns:

        pollutant_counts = (
            df["parameter"]
            .value_counts()
        )

        print(
            pollutant_counts.to_string()
        )


    # -----------------------------------------------------
    # 8. Geographic + temporal coverage
    # -----------------------------------------------------

    print()
    print("[8/8] Geographic and temporal coverage")

    if "latitude" in df.columns:

        print(
            f"Latitude range : "
            f"{df['latitude'].min()} "
            f"to "
            f"{df['latitude'].max()}"
        )

    if "longitude" in df.columns:

        print(
            f"Longitude range: "
            f"{df['longitude'].min()} "
            f"to "
            f"{df['longitude'].max()}"
        )

    if "timestamp_local" in df.columns:

        print(
            f"First timestamp: "
            f"{df['timestamp_local'].min()}"
        )

        print(
            f"Last timestamp : "
            f"{df['timestamp_local'].max()}"
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


    # Coordinates
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

            validation_passed = False

            print(
                f"Invalid coordinates: "
                f"{invalid_coordinates}"
            )

        else:

            print("Geographic coordinates valid")


    # Numeric values
    if "value" in df.columns:

        numeric_values = pd.to_numeric(
            df["value"],
            errors="coerce"
        )

        invalid_values = numeric_values.isna().sum()

        if invalid_values > 0:

            print(
                f"Non-numeric measurement values: "
                f"{invalid_values}"
            )

        else:

            print("Measurement values numeric")


    print()

    if validation_passed:

        print(
            "RAW AIR-QUALITY DATA VALIDATION PASSED"
        )

        print(
            "Step 7 is complete."
        )

    else:

        print(
            "VALIDATION NEEDS ATTENTION"
        )

        print(
            "Do not modify the raw data yet."
        )

    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    validate_air_quality_data()