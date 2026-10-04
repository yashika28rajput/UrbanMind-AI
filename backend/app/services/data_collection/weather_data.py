import requests
import pandas as pd
from pathlib import Path


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "weather"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "delhi_weather.csv"
)


# =========================================================
# DELHI CONFIGURATION
# =========================================================

DELHI_LATITUDE = 28.6139
DELHI_LONGITUDE = 77.2090

API_URL = "https://archive-api.open-meteo.com/v1/archive"


# =========================================================
# DATE CONFIGURATION
# =========================================================

START_DATE = "2026-07-01"
END_DATE = "2026-07-31"


# =========================================================
# WEATHER DATA COLLECTION
# =========================================================

def collect_weather_data():

    print()
    print("=" * 70)
    print("URBANMIND AI - DELHI WEATHER DATA COLLECTION")
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    params = {

        "latitude": DELHI_LATITUDE,

        "longitude": DELHI_LONGITUDE,

        "start_date": START_DATE,

        "end_date": END_DATE,

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "surface_pressure,"
            "wind_speed_10m,"
            "wind_direction_10m"
        ),

        "timezone": "Asia/Kolkata"
    }

    print()
    print("Connecting to Open-Meteo...")
    print()

    try:

        response = requests.get(
            API_URL,
            params=params,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        print("Weather API connection successful.")

    except requests.exceptions.RequestException as error:

        print()
        print("ERROR: Weather API request failed.")
        print(error)

        return


    # =====================================================
    # CHECK HOURLY DATA
    # =====================================================

    if "hourly" not in data:

        print()
        print("ERROR: Hourly weather data not found.")

        return


    hourly_data = data["hourly"]


    # =====================================================
    # CREATE DATAFRAME
    # =====================================================

    df = pd.DataFrame(hourly_data)


    # =====================================================
    # ADD LOCATION INFORMATION
    # =====================================================

    df["city"] = "Delhi"

    df["latitude"] = DELHI_LATITUDE

    df["longitude"] = DELHI_LONGITUDE


    # =====================================================
    # RENAME COLUMNS
    # =====================================================

    df = df.rename(
        columns={
            "time": "timestamp_local",
            "temperature_2m": "temperature_c",
            "relative_humidity_2m": "relative_humidity_percent",
            "precipitation": "precipitation_mm",
            "surface_pressure": "surface_pressure_hpa",
            "wind_speed_10m": "wind_speed_kmh",
            "wind_direction_10m": "wind_direction_degrees"
        }
    )


    # =====================================================
    # COLUMN ORDER
    # =====================================================

    columns = [
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

    df = df[columns]


    # =====================================================
    # SAVE DATA
    # =====================================================

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )


    # =====================================================
    # COLLECTION SUMMARY
    # =====================================================

    print()
    print("=" * 70)
    print("WEATHER DATA COLLECTION COMPLETE")
    print("=" * 70)

    print()
    print(f"Records collected : {len(df)}")

    print()
    print(f"Output file:")
    print(OUTPUT_FILE)

    print()
    print("Columns:")
    print(df.columns.tolist())

    print()
    print("First record:")
    print(df.head(1).to_string(index=False))

    print()
    print("Last record:")
    print(df.tail(1).to_string(index=False))

    print()
    print("=" * 70)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    collect_weather_data()