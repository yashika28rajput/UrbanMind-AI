import json

from fastapi.testclient import TestClient

from app.api import digital_twin as digital_twin_api
from app.main import app


def test_geojson_map_fields_use_overlaid_digital_twin_metrics(monkeypatch) -> None:
    with digital_twin_api.WARD_GEOJSON_PATH.open("r", encoding="utf-8") as source:
        boundaries = json.load(source)
    properties = boundaries["features"][0]["properties"]
    ward_number = int(properties["Ward_No"])
    model = {
        "city": "Delhi",
        "phase": "test",
        "summary": {},
        "wards": [{
            "ward_no": ward_number,
            "aqi": 0.0,
            "temperature": 12.5,
            "green_cover": 30.0,
            "health_risk": 0.2,
            "population": 100,
        }],
    }
    monkeypatch.setattr(digital_twin_api, "get_virtual_city_model", lambda: model)

    response = TestClient(app).get("/api/v1/digital-twin/wards/geojson")

    assert response.status_code == 200, response.text
    feature = next(
        feature for feature in response.json()["features"]
        if int(feature["properties"]["Ward_No"]) == ward_number
    )
    assert feature["properties"]["aqi"] == 0
    assert feature["properties"]["final_AQI"] == 0
    assert feature["properties"]["temperature"] == 12.5
    assert feature["properties"]["mean_LST_C"] == 12.5
