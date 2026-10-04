import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openaq import OpenAQ


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ENV_FILE = PROJECT_ROOT / "backend" / ".env"

STATIONS_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "air_quality"
    / "delhi_monitoring_stations.csv"
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
# REQUIRED POLLUTANTS
# =========================================================

TARGET_PARAMETERS = {
    "pm25",
    "pm10",
    "no2",
    "so2",
    "co",
    "o3"
}


# =========================================================
# GET SENSORS FOR DELHI STATIONS
# =========================================================

def collect_delhi_sensors():

    # -----------------------------------------------------
    # Check stations file
    # -----------------------------------------------------

    if not STATIONS_FILE.exists():

        raise FileNotFoundError(
            "Delhi monitoring stations file not found.\n"
            "Run Step 4 first."
        )

    stations_df = pd.read_csv(
        STATIONS_FILE
    )

    print()
    print("=" * 65)
    print("DELHI SENSOR COLLECTION")
    print("=" * 65)

    print(
        f"Stations to process: {len(stations_df)}"
    )

    print()


    # -----------------------------------------------------
    # Connect to OpenAQ
    # -----------------------------------------------------

    all_sensors = []

    with OpenAQ(api_key=API_KEY) as client:

        for index, station in stations_df.iterrows():

            location_id = int(
                station["location_id"]
            )

            station_name = station[
                "station_name"
            ]

            print(
                f"[{index + 1}/{len(stations_df)}] "
                f"{station_name}"
            )

            try:

                response = client.locations.sensors(
                    location_id
                )

                for sensor in response.results:

                    # -------------------------------------
                    # Parameter information
                    # -------------------------------------

                    parameter = sensor.parameter

                    if parameter is None:
                        continue

                    parameter_name = (
                        parameter.name
                        .lower()
                        .replace(".", "")
                        .replace(" ", "")
                    )

                    # -------------------------------------
                    # Keep only required pollutants
                    # -------------------------------------

                    if parameter_name not in TARGET_PARAMETERS:
                        continue

                    all_sensors.append(
                        {
                            "location_id": location_id,
                            "station_name": station_name,
                            "sensor_id": sensor.id,
                            "parameter": parameter.name,
                            "units": parameter.units
                            if parameter.units
                            else None,
                            "display_name": parameter.display_name
                            if parameter.display_name
                            else None
                        }
                    )

            except Exception as e:

                print(
                    f"   Warning: {e}"
                )

    # =====================================================
    # CREATE DATAFRAME
    # =====================================================

    sensors_df = pd.DataFrame(
        all_sensors
    )

    if sensors_df.empty:

        print()
        print(
            "No target pollutant sensors were found."
        )

        return


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    sensors_df = sensors_df.drop_duplicates(
        subset=[
            "location_id",
            "sensor_id"
        ]
    )


    # =====================================================
    # SAVE SENSOR DATA
    # =====================================================

    output_file = (
        OUTPUT_DIR
        / "delhi_air_quality_sensors.csv"
    )

    sensors_df.to_csv(
        output_file,
        index=False
    )


    # =====================================================
    # DISPLAY RESULTS
    # =====================================================

    print()
    print("=" * 65)
    print("SENSOR COLLECTION COMPLETED")
    print("=" * 65)

    print(
        f"Total sensors found: {len(sensors_df)}"
    )

    print(
        f"Saved to: {output_file}"
    )

    print("=" * 65)

    print()

    print(
        sensors_df[
            [
                "location_id",
                "station_name",
                "sensor_id",
                "parameter",
                "units"
            ]
        ].to_string(index=False)
    )

    print()

    print("=" * 65)
    print("AVAILABLE POLLUTANTS")
    print("=" * 65)

    print(
        sensors_df["parameter"]
        .value_counts()
        .to_string()
    )

    print()

    print("=" * 65)
    print("STEP 5 COMPLETED")
    print("=" * 65)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    collect_delhi_sensors()