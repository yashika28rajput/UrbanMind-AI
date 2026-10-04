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

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "air_quality"

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# LOAD OPENAQ API KEY
# =========================================================

load_dotenv(ENV_FILE)

API_KEY = os.getenv("OPENAQ_API_KEY")

if not API_KEY:
    raise ValueError(
        "OPENAQ_API_KEY not found in backend/.env"
    )


# =========================================================
# DELHI LOCATION
# =========================================================

DELHI_LATITUDE = 28.6139
DELHI_LONGITUDE = 77.2090

# OpenAQ maximum supported radius is 25 km
SEARCH_RADIUS_METERS = 25000


# =========================================================
# FIND DELHI MONITORING STATIONS
# =========================================================

def find_delhi_locations():

    print("Connecting to OpenAQ...")

    try:

        with OpenAQ(api_key=API_KEY) as client:

            response = client.locations.list(
                coordinates=(
                    DELHI_LATITUDE,
                    DELHI_LONGITUDE
                ),
                radius=SEARCH_RADIUS_METERS,
                limit=1000
            )

            records = []

            for location in response.results:

                # -----------------------------------------
                # Coordinates
                # -----------------------------------------

                latitude = None
                longitude = None

                if location.coordinates:

                    latitude = location.coordinates.latitude
                    longitude = location.coordinates.longitude

                # -----------------------------------------
                # Country
                # -----------------------------------------

                country_name = None

                if location.country:
                    country_name = location.country.name

                # -----------------------------------------
                # First measurement
                # -----------------------------------------

                first_measurement = None

                if location.datetime_first:
                    first_measurement = (
                        location.datetime_first.local
                    )

                # -----------------------------------------
                # Last measurement
                # -----------------------------------------

                last_measurement = None

                if location.datetime_last:
                    last_measurement = (
                        location.datetime_last.local
                    )

                # -----------------------------------------
                # Store station
                # -----------------------------------------

                records.append(
                    {
                        "location_id": location.id,
                        "station_name": location.name,
                        "locality": location.locality,
                        "country": country_name,
                        "latitude": latitude,
                        "longitude": longitude,
                        "timezone": location.timezone,

                        # Correct OpenAQ SDK attributes
                        "is_mobile": location.is_mobile,
                        "is_monitor": location.is_monitor,

                        "first_measurement": first_measurement,
                        "last_measurement": last_measurement
                    }
                )

    except Exception as e:

        print()
        print("ERROR while communicating with OpenAQ:")
        print(e)

        return


    # =====================================================
    # CREATE DATAFRAME
    # =====================================================

    df = pd.DataFrame(records)

    if df.empty:

        print()
        print("No Delhi monitoring stations were found.")

        return


    # =====================================================
    # DATA CLEANING
    # =====================================================

    # Remove stations without coordinates
    df = df.dropna(
        subset=[
            "latitude",
            "longitude"
        ]
    )

    # Remove duplicate stations
    df = df.drop_duplicates(
        subset=["location_id"]
    )


    # =====================================================
    # SAVE CSV
    # =====================================================

    output_file = (
        OUTPUT_DIR /
        "delhi_monitoring_stations.csv"
    )

    df.to_csv(
        output_file,
        index=False
    )


    # =====================================================
    # DISPLAY RESULTS
    # =====================================================

    print()
    print("=" * 60)
    print("DELHI MONITORING STATIONS FOUND")
    print("=" * 60)

    print(
        f"Total stations : {len(df)}"
    )

    print(
        f"Saved to       : {output_file}"
    )

    print("=" * 60)

    print()

    print(
        df[
            [
                "location_id",
                "station_name",
                "latitude",
                "longitude"
            ]
        ].to_string(index=False)
    )

    print()
    print("=" * 60)
    print("STEP 4 COMPLETED SUCCESSFULLY")
    print("=" * 60)


# =========================================================
# PROGRAM ENTRY POINT
# =========================================================

if __name__ == "__main__":

    find_delhi_locations()