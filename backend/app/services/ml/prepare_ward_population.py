import os
import pandas as pd


# ================================================================
# UrbanMind AI - Ward Population Preparation
# ================================================================

print("=" * 70)
print("UrbanMind AI - Ward Population Preparation")
print("=" * 70)


# ----------------------------------------------------------------
# Paths
# ----------------------------------------------------------------

INPUT_FILE = "data/processed/population/delhi_population.csv"

OUTPUT_DIR = "data/processed/population"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_population.csv"
)


# ----------------------------------------------------------------
# Required columns
# ----------------------------------------------------------------

REQUIRED_COLUMNS = [
    "Ward",
    "No_HH",
    "TOT_P",
    "TOT_M",
    "TOT_F",
    "P_06",
    "P_LIT",
    "P_ILL"
]


# ----------------------------------------------------------------
# Check input file
# ----------------------------------------------------------------

print("\nChecking input file...")

if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(
        f"Population file not found:\n{INPUT_FILE}"
    )

print("Population file: FOUND")


# ----------------------------------------------------------------
# Load data
# ----------------------------------------------------------------

print("\nLoading population data...")

df = pd.read_csv(INPUT_FILE)

print(f"Input records: {len(df)}")
print(f"Input columns: {df.columns.tolist()}")


# ----------------------------------------------------------------
# Validate columns
# ----------------------------------------------------------------

missing_columns = [
    col for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

print("Required columns: PASSED")


# ----------------------------------------------------------------
# Prepare Ward number
# ----------------------------------------------------------------

print("\nPreparing Ward numbers...")

df["Ward"] = pd.to_numeric(
    df["Ward"],
    errors="coerce"
)

invalid_wards = df["Ward"].isna().sum()

print(f"Invalid Ward records: {invalid_wards}")

if invalid_wards > 0:
    df = df.dropna(subset=["Ward"]).copy()

df["Ward"] = df["Ward"].astype(int)

print("Ward normalization: PASSED")


# ----------------------------------------------------------------
# Validate population columns
# ----------------------------------------------------------------

print("\nValidating population values...")

for column in REQUIRED_COLUMNS[1:]:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

missing_values = df[REQUIRED_COLUMNS[1:]].isna().sum()

print(missing_values)

if missing_values.sum() > 0:
    raise ValueError(
        "Missing/non-numeric population values found."
    )

print("Population value validation: PASSED")


# ----------------------------------------------------------------
# Check negative values
# ----------------------------------------------------------------

print("\nChecking negative population values...")

negative_counts = {}

for column in REQUIRED_COLUMNS[1:]:
    count = (df[column] < 0).sum()
    negative_counts[column] = count

    if count > 0:
        raise ValueError(
            f"Negative values found in column: {column}"
        )

print("Negative-value validation: PASSED")


# ----------------------------------------------------------------
# Aggregate by Ward
# ----------------------------------------------------------------

print("\nAggregating population by Ward...")

ward_population = (
    df.groupby("Ward", as_index=False)[
        [
            "No_HH",
            "TOT_P",
            "TOT_M",
            "TOT_F",
            "P_06",
            "P_LIT",
            "P_ILL"
        ]
    ]
    .sum()
)


# ----------------------------------------------------------------
# Rename Ward column
# ----------------------------------------------------------------

ward_population = ward_population.rename(
    columns={
        "Ward": "Ward_No"
    }
)


# ----------------------------------------------------------------
# Add derived indicators
# ----------------------------------------------------------------

print("\nCreating population indicators...")

ward_population["female_population_percent"] = (
    ward_population["TOT_F"]
    / ward_population["TOT_P"]
    * 100
)

ward_population["male_population_percent"] = (
    ward_population["TOT_M"]
    / ward_population["TOT_P"]
    * 100
)

ward_population["children_percent"] = (
    ward_population["P_06"]
    / ward_population["TOT_P"]
    * 100
)

ward_population["literacy_percent"] = (
    ward_population["P_LIT"]
    / ward_population["TOT_P"]
    * 100
)

ward_population["illiteracy_percent"] = (
    ward_population["P_ILL"]
    / ward_population["TOT_P"]
    * 100
)


# ----------------------------------------------------------------
# Validate population totals
# ----------------------------------------------------------------

print("\nValidating population totals...")

check_population = (
    ward_population["TOT_M"]
    + ward_population["TOT_F"]
)

population_difference = (
    ward_population["TOT_P"]
    - check_population
).abs()

print(
    "Maximum population consistency difference:",
    population_difference.max()
)

if population_difference.max() > 1:
    raise ValueError(
        "TOT_P does not match TOT_M + TOT_F."
    )

print("Population consistency: PASSED")


# ----------------------------------------------------------------
# Validate percentages
# ----------------------------------------------------------------

percentage_columns = [
    "female_population_percent",
    "male_population_percent",
    "children_percent",
    "literacy_percent",
    "illiteracy_percent"
]

for column in percentage_columns:
    if not ward_population[column].between(
        0,
        100
    ).all():
        raise ValueError(
            f"Invalid percentage values in {column}"
        )

print("Percentage validation: PASSED")


# ----------------------------------------------------------------
# Check duplicates
# ----------------------------------------------------------------

print("\nChecking duplicate wards...")

duplicate_count = (
    ward_population["Ward_No"]
    .duplicated()
    .sum()
)

print(f"Duplicate wards: {duplicate_count}")

if duplicate_count > 0:
    raise ValueError(
        "Duplicate Ward_No values found."
    )

print("Duplicate validation: PASSED")


# ----------------------------------------------------------------
# Check Ward range
# ----------------------------------------------------------------

print("\nChecking Ward coverage...")

print(
    f"Minimum Ward_No: {ward_population['Ward_No'].min()}"
)

print(
    f"Maximum Ward_No: {ward_population['Ward_No'].max()}"
)

print(
    f"Unique wards: {ward_population['Ward_No'].nunique()}"
)


# ----------------------------------------------------------------
# Infinite-value validation
# ----------------------------------------------------------------

print("\nChecking infinite values...")

numeric_columns = ward_population.select_dtypes(
    include="number"
).columns

for column in numeric_columns:
    infinite_count = (
        ~pd.Series(
            ward_population[column]
        ).map(
            lambda x: pd.isna(x) or __import__("math").isfinite(x)
        )
    ).sum()

    print(
        f"{column}: {infinite_count}"
    )

    if infinite_count > 0:
        raise ValueError(
            f"Infinite values found in {column}"
        )

print("Infinite-value validation: PASSED")


# ----------------------------------------------------------------
# Save output
# ----------------------------------------------------------------

print("\nSaving ward population dataset...")

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

ward_population.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"Ward population CSV saved:\n{OUTPUT_FILE}"
)


# ----------------------------------------------------------------
# Final validation
# ----------------------------------------------------------------

print("\n" + "=" * 70)
print("FINAL WARD POPULATION VALIDATION")
print("=" * 70)

print(
    f"Rows available: {len(ward_population) > 0}"
)

print(
    f"Unique Ward_No: "
    f"{ward_population['Ward_No'].nunique() == len(ward_population)}"
)

print(
    f"No missing values: "
    f"{not ward_population.isna().any().any()}"
)

print(
    f"Population values valid: "
    f"{(ward_population['TOT_P'] >= 0).all()}"
)

print(
    f"Output exists: "
    f"{os.path.exists(OUTPUT_FILE)}"
)


# ----------------------------------------------------------------
# Summary
# ----------------------------------------------------------------

print("\n" + "=" * 70)
print("WARD POPULATION SUMMARY")
print("=" * 70)

print(
    f"Wards: {len(ward_population)}"
)

print(
    f"Total households: "
    f"{ward_population['No_HH'].sum():,.0f}"
)

print(
    f"Total population: "
    f"{ward_population['TOT_P'].sum():,.0f}"
)

print(
    f"Total male population: "
    f"{ward_population['TOT_M'].sum():,.0f}"
)

print(
    f"Total female population: "
    f"{ward_population['TOT_F'].sum():,.0f}"
)

print(
    f"Total children (0-6): "
    f"{ward_population['P_06'].sum():,.0f}"
)

print(
    f"Total literate population: "
    f"{ward_population['P_LIT'].sum():,.0f}"
)

print(
    f"Total illiterate population: "
    f"{ward_population['P_ILL'].sum():,.0f}"
)


print("\nFirst 10 ward records:")
print(
    ward_population.head(10).to_string(
        index=False
    )
)

print("\n" + "=" * 70)
print("WARD POPULATION PREPARATION COMPLETED SUCCESSFULLY")
print("=" * 70)