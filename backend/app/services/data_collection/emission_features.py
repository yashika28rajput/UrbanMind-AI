import os
import numpy as np
import pandas as pd
import geopandas as gpd


print("=" * 42)
print("UrbanMind AI - Ward Emission Features")
print("=" * 42)


# =========================================================
# Paths
# =========================================================

TRAFFIC_PATH = (
    "data/processed/gis/"
    "delhi_ward_traffic_features.geojson"
)

LULC_PATH = (
    "data/processed/satellite/"
    "delhi_ward_lulc.csv"
)

LST_PATH = (
    "data/processed/satellite/"
    "delhi_ward_lst.csv"
)

POPULATION_PATH = (
    "data/processed/population/"
    "delhi_population_ward_gis.geojson"
)

OUTPUT_DIR = "data/processed/emissions"

OUTPUT_PATH = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_emission_features.geojson"
)


# =========================================================
# Helper Functions
# =========================================================

def normalize_ward_id(df):
    """
    Convert Ward_No into standard int64 format.
    """

    df = df.copy()

    df["Ward_No"] = pd.to_numeric(
        df["Ward_No"],
        errors="coerce"
    )

    df = df[
        df["Ward_No"].notna()
    ].copy()

    df["Ward_No"] = (
        df["Ward_No"]
        .astype(np.int64)
    )

    return df


def find_column(
    df,
    possible_names,
    required=True
):
    """
    Find the first available column.
    """

    for name in possible_names:

        if name in df.columns:
            return name

    if required:

        raise KeyError(
            f"None of these columns found: "
            f"{possible_names}\n"
            f"Available columns: "
            f"{list(df.columns)}"
        )

    return None


def min_max_normalize(series):
    """
    Min-max normalization between 0 and 1.
    """

    minimum = series.min()
    maximum = series.max()

    if (
        pd.isna(minimum)
        or
        pd.isna(maximum)
    ):

        return pd.Series(
            np.zeros(len(series)),
            index=series.index
        )

    if maximum == minimum:

        return pd.Series(
            np.zeros(len(series)),
            index=series.index
        )

    return (
        (series - minimum)
        /
        (maximum - minimum)
    )


# =========================================================
# Load Traffic Data
# =========================================================

print("\nLoading ward traffic features...")

traffic_gdf = gpd.read_file(
    TRAFFIC_PATH
)

print(
    f"Traffic records: "
    f"{len(traffic_gdf)}"
)

print("Traffic columns:")
print(
    list(traffic_gdf.columns)
)


# =========================================================
# Load LULC Data
# =========================================================

print("\nLoading ward LULC features...")

lulc = pd.read_csv(
    LULC_PATH
)

print(
    f"LULC records: "
    f"{len(lulc)}"
)


# =========================================================
# Load LST Data
# =========================================================

print("\nLoading ward LST features...")

lst = pd.read_csv(
    LST_PATH
)

print(
    f"LST records: "
    f"{len(lst)}"
)


# =========================================================
# Load Population Data
# =========================================================

print("\nLoading ward population features...")

population_gdf = gpd.read_file(
    POPULATION_PATH
)

print(
    f"Population records: "
    f"{len(population_gdf)}"
)


# =========================================================
# Normalize Ward IDs
# =========================================================

print("\nNormalizing ward IDs...")

traffic_gdf = normalize_ward_id(
    traffic_gdf
)

lulc = normalize_ward_id(
    lulc
)

lst = normalize_ward_id(
    lst
)

population_gdf = normalize_ward_id(
    population_gdf
)

print("Ward IDs normalized to int64")


# =========================================================
# Remove Duplicate Wards
# =========================================================

traffic_gdf = (
    traffic_gdf
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)

lulc = (
    lulc
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)

lst = (
    lst
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)

population_gdf = (
    population_gdf
    .drop_duplicates(
        subset="Ward_No"
    )
    .copy()
)


# =========================================================
# Identify Traffic Columns
# =========================================================

print("\nIdentifying traffic columns...")


ward_name_column = find_column(
    traffic_gdf,
    [
        "Ward_Name",
        "ward_name",
        "WardName"
    ],
    required=False
)


road_segment_column = find_column(
    traffic_gdf,
    [
        "road_segment_count",
        "road_segments",
        "road_segment",
        "segment_count"
    ],
    required=False
)


total_length_column = find_column(
    traffic_gdf,
    [
        "total_road_length_km",
        "total_road_length_m",
        "road_length_km",
        "road_length_m"
    ]
)


primary_length_column = find_column(
    traffic_gdf,
    [
        "primary_road_length_km",
        "primary_road_length_m"
    ],
    required=False
)


secondary_length_column = find_column(
    traffic_gdf,
    [
        "secondary_road_length_km",
        "secondary_road_length_m"
    ],
    required=False
)


tertiary_length_column = find_column(
    traffic_gdf,
    [
        "tertiary_road_length_km",
        "tertiary_road_length_m"
    ],
    required=False
)


residential_length_column = find_column(
    traffic_gdf,
    [
        "residential_road_length_km",
        "residential_road_length_m"
    ],
    required=False
)


major_length_column = find_column(
    traffic_gdf,
    [
        "major_road_length_km",
        "major_road_length_m"
    ],
    required=False
)


oneway_segments_column = find_column(
    traffic_gdf,
    [
        "oneway_road_segments",
        "oneway_segments"
    ],
    required=False
)


average_segment_column = find_column(
    traffic_gdf,
    [
        "average_road_segment_length_m",
        "average_segment_length_m",
        "average_road_segment_length_km"
    ],
    required=False
)


oneway_fraction_column = find_column(
    traffic_gdf,
    [
        "oneway_fraction",
        "one_way_fraction"
    ],
    required=False
)


print(
    "Traffic columns identified successfully"
)


# =========================================================
# Convert Traffic GeoDataFrame to DataFrame
# =========================================================

print(
    "\nPreparing traffic attributes..."
)

traffic = pd.DataFrame()


traffic["Ward_No"] = (
    traffic_gdf["Ward_No"]
    .astype(np.int64)
)


# Ward name

if ward_name_column:

    traffic["Ward_Name"] = (
        traffic_gdf[
            ward_name_column
        ].astype(str)
    )

else:

    traffic["Ward_Name"] = (
        "Ward "
        +
        traffic["Ward_No"].astype(str)
    )


# Road segment count

if road_segment_column:

    traffic[
        "road_segment_count"
    ] = pd.to_numeric(
        traffic_gdf[
            road_segment_column
        ],
        errors="coerce"
    ).fillna(0)

else:

    traffic[
        "road_segment_count"
    ] = 0


# =========================================================
# Total Road Length
# =========================================================

total_length = pd.to_numeric(
    traffic_gdf[
        total_length_column
    ],
    errors="coerce"
).fillna(0)


if total_length_column.endswith(
    "_km"
):

    traffic[
        "total_road_length_m"
    ] = (
        total_length * 1000
    )

else:

    traffic[
        "total_road_length_m"
    ] = total_length


# =========================================================
# Road Type Length Helper
# =========================================================

def add_length_column(
    output_name,
    source_column
):

    if source_column is None:

        traffic[
            output_name
        ] = 0.0

        return

    values = pd.to_numeric(
        traffic_gdf[
            source_column
        ],
        errors="coerce"
    ).fillna(0)

    if source_column.endswith(
        "_km"
    ):

        values = values * 1000

    traffic[
        output_name
    ] = values


add_length_column(
    "primary_road_length_m",
    primary_length_column
)

add_length_column(
    "secondary_road_length_m",
    secondary_length_column
)

add_length_column(
    "tertiary_road_length_m",
    tertiary_length_column
)

add_length_column(
    "residential_road_length_m",
    residential_length_column
)

add_length_column(
    "major_road_length_m",
    major_length_column
)


# =========================================================
# Derive Major Road Length
# =========================================================

if major_length_column is None:

    print(
        "Major road length not found."
    )

    print(
        "Deriving major road length "
        "from primary + secondary + tertiary."
    )

    traffic[
        "major_road_length_m"
    ] = (
        traffic[
            "primary_road_length_m"
        ]
        +
        traffic[
            "secondary_road_length_m"
        ]
        +
        traffic[
            "tertiary_road_length_m"
        ]
    )


# =========================================================
# One-Way Segments
# =========================================================

if oneway_segments_column:

    traffic[
        "oneway_road_segments"
    ] = pd.to_numeric(
        traffic_gdf[
            oneway_segments_column
        ],
        errors="coerce"
    ).fillna(0)

else:

    traffic[
        "oneway_road_segments"
    ] = 0


# =========================================================
# Average Road Segment Length
# =========================================================

if average_segment_column:

    average_values = pd.to_numeric(
        traffic_gdf[
            average_segment_column
        ],
        errors="coerce"
    ).fillna(0)

    if average_segment_column.endswith(
        "_km"
    ):

        average_values = (
            average_values * 1000
        )

    traffic[
        "average_road_segment_length_m"
    ] = average_values

else:

    traffic[
        "average_road_segment_length_m"
    ] = np.where(
        traffic[
            "road_segment_count"
        ] > 0,

        traffic[
            "total_road_length_m"
        ]
        /
        traffic[
            "road_segment_count"
        ],

        0
    )


# =========================================================
# One-Way Fraction
# =========================================================

if oneway_fraction_column:

    traffic[
        "oneway_fraction"
    ] = pd.to_numeric(
        traffic_gdf[
            oneway_fraction_column
        ],
        errors="coerce"
    ).fillna(0)

else:

    traffic[
        "oneway_fraction"
    ] = np.where(
        traffic[
            "road_segment_count"
        ] > 0,

        traffic[
            "oneway_road_segments"
        ]
        /
        traffic[
            "road_segment_count"
        ],

        0
    )


# =========================================================
# Ensure Traffic Ward IDs
# =========================================================

traffic["Ward_No"] = (
    traffic["Ward_No"]
    .astype(np.int64)
)


# =========================================================
# Prepare LULC
# =========================================================

print(
    "\nPreparing LULC attributes..."
)

lulc_columns = [
    "Ward_No",
    "trees",
    "grass",
    "crops",
    "shrub_and_scrub",
    "built",
    "bare",
    "vegetation",
    "built_environment",
    "water_surface"
]

missing_lulc = [
    column
    for column in lulc_columns
    if column not in lulc.columns
]

if missing_lulc:

    raise KeyError(
        f"Missing LULC columns: "
        f"{missing_lulc}"
    )

lulc = lulc[
    lulc_columns
].copy()

lulc["Ward_No"] = (
    lulc["Ward_No"]
    .astype(np.int64)
)


# =========================================================
# Prepare LST
# =========================================================

print(
    "\nPreparing LST attributes..."
)

if "mean_LST_C" not in lst.columns:

    raise KeyError(
        "mean_LST_C column not found "
        "in LST dataset"
    )

lst = lst[
    [
        "Ward_No",
        "mean_LST_C"
    ]
].copy()

lst["Ward_No"] = (
    lst["Ward_No"]
    .astype(np.int64)
)

lst["mean_LST_C"] = pd.to_numeric(
    lst["mean_LST_C"],
    errors="coerce"
)


# =========================================================
# Prepare Population
# =========================================================

print(
    "\nPreparing population attributes..."
)

population_columns = [
    "Ward_No",
    "TOT_P",
    "No_HH",
    "TOT_M",
    "TOT_F"
]

missing_population = [
    column
    for column in population_columns
    if column not in population_gdf.columns
]

if missing_population:

    raise KeyError(
        f"Missing population columns: "
        f"{missing_population}"
    )

population = pd.DataFrame(
    population_gdf[
        population_columns
    ].copy()
)

population["Ward_No"] = (
    population["Ward_No"]
    .astype(np.int64)
)

for column in population_columns[1:]:

    population[column] = pd.to_numeric(
        population[column],
        errors="coerce"
    )


# =========================================================
# Calculate Ward Area
# =========================================================

print(
    "\nCalculating ward areas..."
)

population_geometry = (
    population_gdf[
        [
            "Ward_No",
            "geometry"
        ]
    ].copy()
)

population_geometry[
    "Ward_No"
] = (
    population_geometry[
        "Ward_No"
    ].astype(np.int64)
)

population_geometry = (
    population_geometry
    .to_crs("EPSG:32644")
)

population_geometry[
    "ward_area_km2"
] = (
    population_geometry.geometry.area
    /
    1_000_000
)

population_geometry = pd.DataFrame(
    population_geometry[
        [
            "Ward_No",
            "ward_area_km2"
        ]
    ]
)


# =========================================================
# MERGE 1: Traffic + LULC
# =========================================================

print(
    "\nMerging traffic and LULC..."
)

emission = traffic.merge(
    lulc,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After Traffic + LULC merge: "
    f"{len(emission)} wards"
)


# =========================================================
# MERGE 2: LST
# =========================================================

print(
    "\nMerging LST..."
)

print(
    f"Traffic/LULC Ward_No dtype: "
    f"{emission['Ward_No'].dtype}"
)

print(
    f"LST Ward_No dtype: "
    f"{lst['Ward_No'].dtype}"
)

emission = emission.merge(
    lst,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After LST merge: "
    f"{len(emission)} wards"
)


# =========================================================
# MERGE 3: Population
# =========================================================

print(
    "\nMerging population..."
)

emission = emission.merge(
    population,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After population merge: "
    f"{len(emission)} wards"
)


# =========================================================
# MERGE 4: Ward Area
# =========================================================

print(
    "\nMerging ward area..."
)

emission = emission.merge(
    population_geometry,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

print(
    f"After ward area merge: "
    f"{len(emission)} wards"
)


# =========================================================
# Numeric Conversion
# =========================================================

numeric_columns = [
    "road_segment_count",
    "total_road_length_m",
    "primary_road_length_m",
    "secondary_road_length_m",
    "tertiary_road_length_m",
    "residential_road_length_m",
    "major_road_length_m",
    "oneway_road_segments",
    "average_road_segment_length_m",
    "oneway_fraction",
    "trees",
    "grass",
    "crops",
    "shrub_and_scrub",
    "built",
    "bare",
    "vegetation",
    "built_environment",
    "water_surface",
    "mean_LST_C",
    "TOT_P",
    "No_HH",
    "TOT_M",
    "TOT_F",
    "ward_area_km2"
]

for column in numeric_columns:

    emission[column] = pd.to_numeric(
        emission[column],
        errors="coerce"
    )


# =========================================================
# Population Density
# =========================================================

print(
    "\nCalculating population density..."
)

emission[
    "population_density_per_km2"
] = (
    emission["TOT_P"]
    /
    emission[
        "ward_area_km2"
    ].replace(
        0,
        np.nan
    )
)


# =========================================================
# Road Density
# =========================================================

print(
    "Calculating road density..."
)

emission[
    "road_density_km_per_km2"
] = (
    (
        emission[
            "total_road_length_m"
        ]
        /
        1000
    )
    /
    emission[
        "ward_area_km2"
    ].replace(
        0,
        np.nan
    )
)


# =========================================================
# Major Road Density
# =========================================================

emission[
    "major_road_density_km_per_km2"
] = (
    (
        emission[
            "major_road_length_m"
        ]
        /
        1000
    )
    /
    emission[
        "ward_area_km2"
    ].replace(
        0,
        np.nan
    )
)


# =========================================================
# Road Length Per 1000 Population
# =========================================================

emission[
    "road_length_m_per_1000_population"
] = (
    emission[
        "total_road_length_m"
    ]
    /
    (
        emission[
            "TOT_P"
        ]
        /
        1000
    ).replace(
        0,
        np.nan
    )
)


# =========================================================
# Major Road Length Per 1000 Population
# =========================================================

emission[
    "major_road_length_m_per_1000_population"
] = (
    emission[
        "major_road_length_m"
    ]
    /
    (
        emission[
            "TOT_P"
        ]
        /
        1000
    ).replace(
        0,
        np.nan
    )
)


# =========================================================
# Traffic Activity Proxy
# =========================================================

print(
    "Calculating traffic activity proxy..."
)

emission[
    "traffic_activity_proxy"
] = (
    emission[
        "major_road_length_m"
    ]
    *
    emission[
        "population_density_per_km2"
    ]
)


# =========================================================
# Built Environment Pressure
# =========================================================

print(
    "Calculating built environment pressure..."
)

emission[
    "built_environment_pressure"
] = (
    emission[
        "built_environment"
    ]
    *
    emission[
        "population_density_per_km2"
    ]
)


# =========================================================
# Vegetation Mitigation Proxy
# =========================================================

print(
    "Calculating vegetation mitigation proxy..."
)

emission[
    "vegetation_mitigation_proxy"
] = (
    emission[
        "vegetation"
    ]
    *
    emission[
        "ward_area_km2"
    ]
)


# =========================================================
# Heat-Emission Interaction
# =========================================================

print(
    "Calculating heat-emission interaction..."
)

emission[
    "heat_emission_pressure"
] = (
    emission[
        "traffic_activity_proxy"
    ]
    *
    emission[
        "mean_LST_C"
    ]
)


# =========================================================
# Pressure Indices
# =========================================================

print(
    "\nCreating pressure indices..."
)

emission[
    "traffic_pressure_index"
] = min_max_normalize(
    emission[
        "traffic_activity_proxy"
    ]
)

emission[
    "built_pressure_index"
] = min_max_normalize(
    emission[
        "built_environment_pressure"
    ]
)

emission[
    "heat_pressure_index"
] = min_max_normalize(
    emission[
        "heat_emission_pressure"
    ]
)

emission[
    "vegetation_mitigation_index"
] = min_max_normalize(
    emission[
        "vegetation_mitigation_proxy"
    ]
)


# =========================================================
# Combined Emission Pressure Index
# =========================================================

print(
    "Creating emission pressure index..."
)

emission[
    "emission_pressure_index"
] = (
    0.40
    *
    emission[
        "traffic_pressure_index"
    ]
    +
    0.30
    *
    emission[
        "built_pressure_index"
    ]
    +
    0.30
    *
    emission[
        "heat_pressure_index"
    ]
)


# =========================================================
# Clean Numeric Values
# =========================================================

all_numeric_columns = (
    emission
    .select_dtypes(
        include=[np.number]
    )
    .columns
)

emission[
    all_numeric_columns
] = (
    emission[
        all_numeric_columns
    ]
    .replace(
        [np.inf, -np.inf],
        np.nan
    )
)

emission[
    all_numeric_columns
] = (
    emission[
        all_numeric_columns
    ]
    .fillna(0)
)


# =========================================================
# Attach Geometry
# =========================================================

print(
    "\nAttaching ward geometry..."
)

ward_geometry = (
    population_gdf[
        [
            "Ward_No",
            "geometry"
        ]
    ].copy()
)

ward_geometry["Ward_No"] = (
    ward_geometry["Ward_No"]
    .astype(np.int64)
)

emission = ward_geometry.merge(
    emission,
    on="Ward_No",
    how="inner",
    validate="one_to_one"
)

emission = gpd.GeoDataFrame(
    emission,
    geometry="geometry",
    crs=population_gdf.crs
)


# =========================================================
# Reorder Columns
# =========================================================

preferred_columns = [
    "Ward_No",
    "Ward_Name",
    "TOT_P",
    "No_HH",
    "TOT_M",
    "TOT_F",
    "ward_area_km2",
    "population_density_per_km2",
    "road_segment_count",
    "total_road_length_m",
    "primary_road_length_m",
    "secondary_road_length_m",
    "tertiary_road_length_m",
    "residential_road_length_m",
    "major_road_length_m",
    "oneway_road_segments",
    "average_road_segment_length_m",
    "oneway_fraction",
    "road_density_km_per_km2",
    "major_road_density_km_per_km2",
    "road_length_m_per_1000_population",
    "major_road_length_m_per_1000_population",
    "trees",
    "grass",
    "crops",
    "shrub_and_scrub",
    "built",
    "bare",
    "vegetation",
    "built_environment",
    "water_surface",
    "mean_LST_C",
    "traffic_activity_proxy",
    "built_environment_pressure",
    "vegetation_mitigation_proxy",
    "heat_emission_pressure",
    "traffic_pressure_index",
    "built_pressure_index",
    "heat_pressure_index",
    "vegetation_mitigation_index",
    "emission_pressure_index",
    "geometry"
]

existing_columns = [
    column
    for column in preferred_columns
    if column in emission.columns
]

emission = emission[
    existing_columns
].copy()


# =========================================================
# Validation
# =========================================================

print(
    "\nValidating ward emission dataset..."
)

records = len(emission)

unique_wards = (
    emission[
        "Ward_No"
    ].nunique()
)

duplicate_wards = (
    emission[
        "Ward_No"
    ]
    .duplicated()
    .sum()
)

missing_geometry = (
    emission.geometry.isna()
    .sum()
)

invalid_geometry = (
    (
        ~emission.geometry.is_valid
    )
    .sum()
)

missing_emission_index = (
    emission[
        "emission_pressure_index"
    ]
    .isna()
    .sum()
)

infinite_values = (
    np.isinf(
        emission.select_dtypes(
            include=[np.number]
        )
    )
    .sum()
    .sum()
)


print(
    f"Records: {records}"
)

print(
    f"Unique wards: {unique_wards}"
)

print(
    f"Duplicate wards: {duplicate_wards}"
)

print(
    f"Missing geometries: {missing_geometry}"
)

print(
    f"Invalid geometries: {invalid_geometry}"
)

print(
    "Missing emission index: "
    f"{missing_emission_index}"
)

print(
    "Infinite numeric values: "
    f"{infinite_values}"
)


# =========================================================
# Validation Checks
# =========================================================

if records != 272:

    raise ValueError(
        f"Expected 272 wards, "
        f"found {records}"
    )


if unique_wards != 272:

    raise ValueError(
        f"Expected 272 unique wards, "
        f"found {unique_wards}"
    )


if duplicate_wards != 0:

    raise ValueError(
        "Duplicate Ward_No values detected"
    )


if missing_geometry != 0:

    raise ValueError(
        "Missing ward geometries detected"
    )


if invalid_geometry != 0:

    raise ValueError(
        "Invalid ward geometries detected"
    )


if missing_emission_index != 0:

    raise ValueError(
        "Missing emission pressure "
        "index detected"
    )


if infinite_values != 0:

    raise ValueError(
        "Infinite numeric values detected"
    )


print(
    "Emission feature validation passed"
)


# =========================================================
# Save Dataset
# =========================================================

print(
    "\nSaving ward-level emission features..."
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

emission.to_file(
    OUTPUT_PATH,
    driver="GeoJSON"
)

print(
    f"Saved: {OUTPUT_PATH}"
)


# =========================================================
# Summary
# =========================================================

print(
    "\n" + "=" * 42
)

print(
    "Ward-Level Emission Summary"
)

print(
    "=" * 42
)

print(
    f"Wards: {len(emission)}"
)

print(
    "Average population density "
    "(people/km2): "
    f"{emission['population_density_per_km2'].mean():.2f}"
)

print(
    "Average road density "
    "(km/km2): "
    f"{emission['road_density_km_per_km2'].mean():.2f}"
)

print(
    "Average major road density "
    "(km/km2): "
    f"{emission['major_road_density_km_per_km2'].mean():.2f}"
)

print(
    "Average traffic pressure index: "
    f"{emission['traffic_pressure_index'].mean():.4f}"
)

print(
    "Average built pressure index: "
    f"{emission['built_pressure_index'].mean():.4f}"
)

print(
    "Average heat pressure index: "
    f"{emission['heat_pressure_index'].mean():.4f}"
)

print(
    "Average vegetation mitigation index: "
    f"{emission['vegetation_mitigation_index'].mean():.4f}"
)

print(
    "Average emission pressure index: "
    f"{emission['emission_pressure_index'].mean():.4f}"
)

print(
    "Minimum emission pressure index: "
    f"{emission['emission_pressure_index'].min():.4f}"
)

print(
    "Maximum emission pressure index: "
    f"{emission['emission_pressure_index'].max():.4f}"
)

print(
    "=" * 42
)

print(
    "Ward emission feature extraction completed"
)

print(
    "=" * 42
)