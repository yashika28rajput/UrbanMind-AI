import geopandas as gpd
import pandas as pd


ROAD_FILE = (
    "data/processed/gis/"
    "delhi_traffic_features.geojson"
)

WARD_FILE = (
    "data/raw/gis/"
    "Delhi_Wards.geojson"
)

OUTPUT_FILE = (
    "data/processed/gis/"
    "delhi_ward_traffic_features.geojson"
)


MAJOR_ROAD_TYPES = {
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
}


def load_road_data():
    print("")
    print("Loading Delhi road network...")

    roads = gpd.read_file(
        ROAD_FILE
    )

    print(
        "Road records:",
        len(roads)
    )

    return roads


def load_ward_data():
    print("")
    print("Loading Delhi ward boundaries...")

    wards = gpd.read_file(
        WARD_FILE
    )

    ward_numbers = pd.to_numeric(
        wards["Ward_No"],
        errors="coerce"
    )

    wards = wards[
        ward_numbers.notna()
    ].copy()

    wards["Ward_No"] = ward_numbers[
        ward_numbers.notna()
    ].astype(int)

    wards = wards[
        [
            "Ward_No",
            "Ward_Name",
            "geometry"
        ]
    ]

    wards = wards.drop_duplicates(
        subset=["Ward_No"]
    )

    print(
        "Ward records:",
        len(wards)
    )

    return wards


def prepare_road_features(
    roads
):
    print("")
    print("Preparing road attributes...")

    roads["road_length_m"] = pd.to_numeric(
        roads["road_length_m"],
        errors="coerce"
    )

    roads["road_length_m"] = (
        roads["road_length_m"]
        .fillna(0)
    )

    roads["highway_type"] = (
        roads["highway"]
        .astype(str)
        .str.lower()
        .str.replace(
            "[",
            "",
            regex=False
        )
        .str.replace(
            "]",
            "",
            regex=False
        )
        .str.replace(
            "'",
            "",
            regex=False
        )
        .str.strip()
    )

    roads["oneway_flag"] = (
        roads["oneway"]
        .astype(str)
        .str.lower()
        .isin(
            ["true", "1", "yes"]
        )
        .astype(int)
    )

    roads["major_road_flag"] = (
        roads["highway_type"]
        .isin(MAJOR_ROAD_TYPES)
        .astype(int)
    )

    roads["primary_length_m"] = 0.0
    roads["secondary_length_m"] = 0.0
    roads["tertiary_length_m"] = 0.0
    roads["residential_length_m"] = 0.0
    roads["major_road_length_m"] = 0.0

    roads.loc[
        roads["highway_type"]
        .isin(
            ["primary", "primary_link"]
        ),
        "primary_length_m"
    ] = roads["road_length_m"]

    roads.loc[
        roads["highway_type"]
        .isin(
            ["secondary", "secondary_link"]
        ),
        "secondary_length_m"
    ] = roads["road_length_m"]

    roads.loc[
        roads["highway_type"]
        .isin(
            ["tertiary", "tertiary_link"]
        ),
        "tertiary_length_m"
    ] = roads["road_length_m"]

    roads.loc[
        roads["highway_type"]
        == "residential",
        "residential_length_m"
    ] = roads["road_length_m"]

    roads.loc[
        roads["major_road_flag"] == 1,
        "major_road_length_m"
    ] = roads["road_length_m"]

    print(
        "Road attributes prepared"
    )

    return roads


def perform_spatial_join(
    roads,
    wards
):
    print("")
    print(
        "Assigning roads to Delhi wards..."
    )

    if roads.crs != wards.crs:

        print(
            "Aligning coordinate systems..."
        )

        roads = roads.to_crs(
            wards.crs
        )

    roads = roads[
        roads.geometry.notna()
    ].copy()

    joined = gpd.sjoin(
        roads,
        wards,
        how="inner",
        predicate="intersects"
    )

    print(
        "Road segments assigned:",
        len(joined)
    )

    return joined


def aggregate_traffic_features(
    joined
):
    print("")
    print(
        "Aggregating traffic features by ward..."
    )

    grouped = (
        joined
        .groupby(
            [
                "Ward_No",
                "Ward_Name"
            ],
            as_index=False
        )
        .agg(
            road_segment_count=(
                "road_length_m",
                "count"
            ),
            total_road_length_m=(
                "road_length_m",
                "sum"
            ),
            primary_road_length_m=(
                "primary_length_m",
                "sum"
            ),
            secondary_road_length_m=(
                "secondary_length_m",
                "sum"
            ),
            tertiary_road_length_m=(
                "tertiary_length_m",
                "sum"
            ),
            residential_road_length_m=(
                "residential_length_m",
                "sum"
            ),
            major_road_length_m=(
                "major_road_length_m",
                "sum"
            ),
            oneway_road_segments=(
                "oneway_flag",
                "sum"
            )
        )
    )

    grouped[
        "total_road_length_km"
    ] = (
        grouped[
            "total_road_length_m"
        ] / 1000
    )

    grouped[
        "primary_road_length_km"
    ] = (
        grouped[
            "primary_road_length_m"
        ] / 1000
    )

    grouped[
        "secondary_road_length_km"
    ] = (
        grouped[
            "secondary_road_length_m"
        ] / 1000
    )

    grouped[
        "tertiary_road_length_km"
    ] = (
        grouped[
            "tertiary_road_length_m"
        ] / 1000
    )

    grouped[
        "residential_road_length_km"
    ] = (
        grouped[
            "residential_road_length_m"
        ] / 1000
    )

    grouped[
        "major_road_length_km"
    ] = (
        grouped[
            "major_road_length_m"
        ] / 1000
    )

    grouped[
        "average_road_segment_length_m"
    ] = (
        grouped[
            "total_road_length_m"
        ]
        / grouped[
            "road_segment_count"
        ]
    )

    grouped[
        "oneway_fraction"
    ] = (
        grouped[
            "oneway_road_segments"
        ]
        / grouped[
            "road_segment_count"
        ]
    )

    grouped = grouped.drop(
        columns=[
            "primary_road_length_m",
            "secondary_road_length_m",
            "tertiary_road_length_m",
            "residential_road_length_m",
            "major_road_length_m",
            "total_road_length_m"
        ]
    )

    print(
        "Ward-level traffic features created:",
        len(grouped)
    )

    return grouped


def attach_geometry(
    wards,
    traffic
):
    print("")
    print(
        "Attaching ward geometry..."
    )

    result = wards.merge(
        traffic,
        on=[
            "Ward_No",
            "Ward_Name"
        ],
        how="left",
        validate="one_to_one"
    )

    numeric_columns = [
        "road_segment_count",
        "total_road_length_km",
        "primary_road_length_km",
        "secondary_road_length_km",
        "tertiary_road_length_km",
        "residential_road_length_km",
        "major_road_length_km",
        "oneway_road_segments",
        "average_road_segment_length_m",
        "oneway_fraction"
    ]

    for column in numeric_columns:

        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(0)
        )

    return result


def validate_result(
    result
):
    print("")
    print(
        "Validating ward-level traffic dataset..."
    )

    print(
        "Records:",
        len(result)
    )

    print(
        "Unique wards:",
        result["Ward_No"].nunique()
    )

    print(
        "Duplicate wards:",
        result["Ward_No"]
        .duplicated()
        .sum()
    )

    print(
        "Missing geometries:",
        result.geometry.isna().sum()
    )

    print(
        "Invalid geometries:",
        (~result.geometry.is_valid).sum()
    )

    print(
        "Missing total road length:",
        result[
            "total_road_length_km"
        ].isna().sum()
    )

    if len(result) != 272:
        raise ValueError(
            "Expected exactly 272 wards."
        )

    if result[
        "Ward_No"
    ].duplicated().sum() != 0:

        raise ValueError(
            "Duplicate Ward_No found."
        )

    if result.geometry.isna().sum() != 0:

        raise ValueError(
            "Missing geometry found."
        )

    if (
        (~result.geometry.is_valid)
        .sum()
        != 0
    ):

        raise ValueError(
            "Invalid geometry found."
        )

    print(
        "Traffic feature validation passed"
    )


def save_result(
    result
):
    print("")
    print(
        "Saving ward-level traffic features..."
    )

    result.to_file(
        OUTPUT_FILE,
        driver="GeoJSON"
    )

    print(
        "Saved:",
        OUTPUT_FILE
    )


def print_summary(
    result
):
    print("")
    print(
        "=========================================="
    )

    print(
        "Ward-Level Traffic Summary"
    )

    print(
        "=========================================="
    )

    print(
        "Wards:",
        len(result)
    )

    print(
        "Total road network (km):",
        round(
            result[
                "total_road_length_km"
            ].sum(),
            2
        )
    )

    print(
        "Total major road network (km):",
        round(
            result[
                "major_road_length_km"
            ].sum(),
            2
        )
    )

    print(
        "Average road length per ward (km):",
        round(
            result[
                "total_road_length_km"
            ].mean(),
            2
        )
    )

    print(
        "Average one-way fraction:",
        round(
            result[
                "oneway_fraction"
            ].mean(),
            4
        )
    )


if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        "UrbanMind AI - Ward Traffic Features"
    )

    print(
        "=========================================="
    )

    roads = load_road_data()

    wards = load_ward_data()

    roads = prepare_road_features(
        roads
    )

    joined = perform_spatial_join(
        roads,
        wards
    )

    traffic = aggregate_traffic_features(
        joined
    )

    result = attach_geometry(
        wards,
        traffic
    )

    validate_result(
        result
    )

    save_result(
        result
    )

    print_summary(
        result
    )

    print(
        "=========================================="
    )

    print(
        "Ward traffic feature extraction completed"
    )

    print(
        "=========================================="
    )