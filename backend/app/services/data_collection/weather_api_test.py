import requests
# =========================================================
# OPEN-METEO API TEST
# =========================================================

DELHI_LATITUDE = 28.6139
DELHI_LONGITUDE = 77.2090

API_URL = "https://api.open-meteo.com/v1/forecast"


def test_weather_api():

    print()
    print("=" * 60)
    print("URBANMIND AI - WEATHER API TEST")
    print("=" * 60)

    params = {
        "latitude": DELHI_LATITUDE,
        "longitude": DELHI_LONGITUDE,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation,"
            "surface_pressure,"
            "wind_speed_10m,"
            "wind_direction_10m"
        ),
        "timezone": "Asia/Kolkata"
    }

    try:

        response = requests.get(
            API_URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        print()
        print("API CONNECTION SUCCESSFUL")
        print()

        print("Delhi Weather Data:")
        print(data)

        print()
        print("=" * 60)
        print("WEATHER API TEST PASSED")
        print("=" * 60)

    except requests.exceptions.RequestException as error:

        print()
        print("WEATHER API CONNECTION FAILED")
        print()
        print(error)

        print()
        print("=" * 60)
        print("WEATHER API TEST FAILED")
        print("=" * 60)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    test_weather_api()