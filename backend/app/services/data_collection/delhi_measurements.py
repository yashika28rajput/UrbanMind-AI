import os
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from openaq import OpenAQ


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ENV_FILE = PROJECT_ROOT / "backend" / ".env"

SENSORS_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "air_quality"
    / "delhi_air_quality_sensors.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "air_quality"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# LOAD API KEY
# =========================================================

load_dotenv(ENV_FILE)

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError(
        "OPENAQ_API_KEY not found in backend/.env"
    )


# =========================================================
# DATA COLLECTION PERIOD
# =========================================================

# Start with one month.
# We can expand this later.

START_DATE = "2026-07-01T00:00:00"

END_DATE = "2026-08-01T00:00:00"


# =========================================================
# COLLECT MEASUREMENTS
# =========================================================

def collect_measurements():

    # -----------------------------------------------------
    # Check sensor file
    # -----------------------------------------------------

    if not SENSORS_FILE.exists():

        raise FileNotFoundError(
            "Sensor file not found.\n"
            "Run Step 5 first."
        )

    sensors_df = pd.read_csv(
        SENSORS_FILE
    )

    print()
    print("=" * 70)
    print("DELHI AIR QUALITY MEASUREMENT COLLECTION")
    print("=" * 70)

    print(
        f"Sensors available: {len(sensors_df)}"
    )

    print(
        f"Period: {START_DATE} → {END_DATE}"
    )

    print()


    # -----------------------------------------------------
    # OpenAQ connection
    # -----------------------------------------------------

    all_measurements = []

    with OpenAQ(api_key=API_KEY) as client:

        for index, sensor in sensors_df.iterrows():

            sensor_id = int(
                sensor["sensor_id"]
            )

            location_id = int(
                sensor["location_id"]
            )

            station_name = sensor[
                "station_name"
            ]

            parameter = sensor[
                "parameter"
            ]

            print(
                f"[{index + 1}/{len(sensors_df)}] "
                f"{station_name} | "
                f"{parameter} | "
                f"Sensor {sensor_id}"
            )

            try:

                response = client.measurements.list(
                    sensors_id=sensor_id,
                    data="hours",
                    datetime_from=START_DATE,
                    datetime_to=END_DATE,
                    limit=1000
                )

                for measurement in response.results:

                    # -------------------------------------
                    # Measurement timestamp
                    # -------------------------------------

                    timestamp_utc = None
                    timestamp_local = None

                    if measurement.period:

                        if measurement.period.datetime_from:

                            timestamp_utc = (
                                measurement
                                .period
                                .datetime_from
                                .utc
                            )

                            timestamp_local = (
                                measurement
                                .period
                                .datetime_from
                                .local
                            )

                    # -------------------------------------
                    # Coordinates
                    # -------------------------------------

                    latitude = None
                    longitude = None

                    if measurement.coordinates:

                        latitude = (
                            measurement
                            .coordinates
                            .latitude
                        )

                        longitude = (
                            measurement
                            .coordinates
                            .longitude
                        )

                    # -------------------------------------
                    # Store measurement
                    # -------------------------------------

                    all_measurements.append(
                        {
                            "location_id": location_id,
                            "station_name": station_name,
                            "sensor_id": sensor_id,
                            "parameter": parameter,
                            "value": measurement.value,
                            "units": sensor["units"],
                            "timestamp_utc": timestamp_utc,
                            "timestamp_local": timestamp_local,
                            "latitude": latitude,
                            "longitude": longitude
                        }
                    )

            except Exception as e:

                print(
                    f"   WARNING: {e}"
                )


    # =====================================================
    # CREATE DATAFRAME
    # =====================================================

    measurements_df = pd.DataFrame(
        all_measurements
    )

    if measurements_df.empty:

        print()
        print(
            "No measurements were returned."
        )

        return


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    measurements_df = (
        measurements_df
        .drop_duplicates()
    )


    # =====================================================
    # SORT DATA
    # =====================================================

    measurements_df = (
        measurements_df
        .sort_values(
            by=[
                "timestamp_utc",
                "station_name",
                "parameter"
            ]
        )
        .reset_index(drop=True)
    )


    # =====================================================
    # SAVE DATA
    # =====================================================

    output_file = (
        OUTPUT_DIR
        / "delhi_air_quality_measurements_july_2026.csv"
    )

    measurements_df.to_csv(
        output_file,
        index=False
    )


    # =====================================================
    # DISPLAY SUMMARY
    # =====================================================

    print()
    print("=" * 70)
    print("MEASUREMENT COLLECTION COMPLETED")
    print("=" * 70)

    print(
        f"Total measurements: "
        f"{len(measurements_df)}"
    )

    print(
        f"Saved to: {output_file}"
    )

    print()
    print("Measurements by pollutant:")

    print(
        measurements_df[
            "parameter"
        ].value_counts().to_string()
    )

    print()
    print("Date range:")

    print(
        measurements_df[
            "timestamp_local"
        ].min()
    )

    print(
        "to"
    )

    print(
        measurements_df[
            "timestamp_local"
        ].max()
    )

    print()
    print("=" * 70)
    print("STEP 6 COMPLETED")
    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    collect_measurements()