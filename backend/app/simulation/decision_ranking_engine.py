"""
UrbanMind AI - Decision Ranking Engine

Purpose:
    Rank intervention scenarios for each Delhi ward using:
    - Heat reduction
    - Emission reduction
    - Intervention potential
    - Combined impact

Input:
    data/processed/scenarios/delhi_intervention_scenarios.csv
    data/processed/urban/delhi_unified_urban_dataset.geojson

Output:
    data/processed/decision/delhi_ward_decision_ranking.csv
    data/processed/decision/delhi_ward_decision_ranking.geojson
    data/processed/decision/decision_ranking_summary.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[3]

SCENARIO_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "scenarios"
    / "delhi_intervention_scenarios.csv"
)

GEOMETRY_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "urban"
    / "delhi_unified_urban_dataset.geojson"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "decision"
)

OUTPUT_CSV = OUTPUT_DIR / "delhi_ward_decision_ranking.csv"
OUTPUT_GEOJSON = OUTPUT_DIR / "delhi_ward_decision_ranking.geojson"
OUTPUT_SUMMARY = OUTPUT_DIR / "decision_ranking_summary.json"


# ============================================================
# REQUIRED COLUMNS
# ============================================================

REQUIRED_SCENARIO_COLUMNS = [
    "Ward_No",
    "Ward_Name",
    "intervention",
    "intervention_potential",
    "baseline_LST_C",
    "simulated_LST_C",
    "estimated_heat_reduction_C",
    "heat_improvement_percent",
    "baseline_emission_pressure",
    "simulated_emission_pressure",
    "estimated_emission_reduction",
    "emission_improvement_percent",
    "combined_impact_score",
]


NUMERIC_COLUMNS = [
    "intervention_potential",
    "baseline_LST_C",
    "simulated_LST_C",
    "estimated_heat_reduction_C",
    "heat_improvement_percent",
    "baseline_emission_pressure",
    "simulated_emission_pressure",
    "estimated_emission_reduction",
    "emission_improvement_percent",
    "combined_impact_score",
]


EXPECTED_INTERVENTIONS = {
    "green_cover",
    "urban_forest",
    "roadside_greening",
    "cool_roof",
    "water_restoration",
    "sustainable_mobility",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_ward_ids(df, column="Ward_No"):
    """
    Convert Ward_No into a consistent integer representation.
    """

    df = df.copy()

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    if df[column].isna().any():
        raise ValueError(
            f"Invalid Ward_No values found in {column}"
        )

    df[column] = df[column].astype(int)

    return df


def check_numeric_columns(df, columns):
    """
    Validate numeric columns for missing or infinite values.
    """

    for column in columns:

        if column not in df.columns:
            raise ValueError(
                f"Required numeric column missing: {column}"
            )

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

        missing = int(df[column].isna().sum())

        infinite = int(
            np.isinf(
                df[column].to_numpy(dtype=float)
            ).sum()
        )

        if missing > 0:
            raise ValueError(
                f"{column}: {missing} missing values"
            )

        if infinite > 0:
            raise ValueError(
                f"{column}: {infinite} infinite values"
            )

    return df


def min_max_normalize(series):
    """
    Normalize a pandas Series to 0-1.
    """

    series = pd.to_numeric(
        series,
        errors="coerce"
    )

    minimum = series.min()
    maximum = series.max()

    if pd.isna(minimum) or pd.isna(maximum):
        return pd.Series(
            0.0,
            index=series.index
        )

    if maximum == minimum:
        return pd.Series(
            1.0,
            index=series.index
        )

    return (
        (series - minimum)
        / (maximum - minimum)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("UrbanMind AI - Decision Ranking Engine")
    print("=" * 65)

    # --------------------------------------------------------
    # CREATE OUTPUT DIRECTORY
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # CHECK INPUT FILES
    # --------------------------------------------------------

    print("\nChecking input files...")

    if SCENARIO_FILE.exists():
        print("Scenario dataset: FOUND")
    else:
        raise FileNotFoundError(
            f"Scenario dataset not found:\n{SCENARIO_FILE}"
        )

    if GEOMETRY_FILE.exists():
        print("Ward geometry: FOUND")
    else:
        raise FileNotFoundError(
            f"Ward geometry not found:\n{GEOMETRY_FILE}"
        )

    # --------------------------------------------------------
    # LOAD SCENARIOS
    # --------------------------------------------------------

    print("\nLoading intervention scenarios...")

    scenarios = pd.read_csv(
        SCENARIO_FILE
    )

    print(
        f"Scenario records: {len(scenarios)}"
    )

    # --------------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_SCENARIO_COLUMNS
        if column not in scenarios.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing_columns)
        )

    print("Required columns: PASSED")

    # --------------------------------------------------------
    # NORMALIZE WARD IDS
    # --------------------------------------------------------

    print("\nNormalizing Ward IDs...")

    scenarios = normalize_ward_ids(
        scenarios
    )

    print(
        "Ward IDs normalized successfully"
    )

    # --------------------------------------------------------
    # CHECK DUPLICATE WARD-INTERVENTION PAIRS
    # --------------------------------------------------------

    print("\nChecking scenario uniqueness...")

    duplicate_pairs = int(
        scenarios.duplicated(
            subset=["Ward_No", "intervention"]
        ).sum()
    )

    print(
        f"Duplicate ward-intervention pairs: "
        f"{duplicate_pairs}"
    )

    if duplicate_pairs != 0:
        raise ValueError(
            "Duplicate ward-intervention pairs found."
        )

    ward_count = scenarios["Ward_No"].nunique()
    intervention_count = scenarios["intervention"].nunique()

    print(
        f"Wards: {ward_count}"
    )

    print(
        f"Interventions: {intervention_count}"
    )

    if ward_count != 272:
        raise ValueError(
            f"Expected 272 wards, found {ward_count}"
        )

    if intervention_count != 6:
        raise ValueError(
            f"Expected 6 interventions, "
            f"found {intervention_count}"
        )

    actual_interventions = set(
        scenarios["intervention"].unique()
    )

    if actual_interventions != EXPECTED_INTERVENTIONS:
        raise ValueError(
            "Unexpected intervention types found.\n"
            f"Expected: {EXPECTED_INTERVENTIONS}\n"
            f"Found: {actual_interventions}"
        )

    expected_scenarios = 272 * 6

    if len(scenarios) != expected_scenarios:
        raise ValueError(
            f"Expected {expected_scenarios} scenarios, "
            f"found {len(scenarios)}"
        )

    print(
        "Scenario coverage validation: PASSED"
    )

    # --------------------------------------------------------
    # VALIDATE NUMERIC VALUES
    # --------------------------------------------------------

    print("\nValidating numeric values...")

    scenarios = check_numeric_columns(
        scenarios,
        NUMERIC_COLUMNS
    )

    print(
        "Numeric validation: PASSED"
    )

    # --------------------------------------------------------
    # LOAD WARD GEOMETRY
    # --------------------------------------------------------

    print("\nLoading ward geometry...")

    wards = gpd.read_file(
        GEOMETRY_FILE
    )

    print(
        f"Ward geometry records: {len(wards)}"
    )

    if "Ward_No" not in wards.columns:
        raise ValueError(
            "Ward_No missing from geometry dataset."
        )

    wards = normalize_ward_ids(
        wards
    )

    geometry_duplicates = int(
        wards.duplicated(
            subset=["Ward_No"]
        ).sum()
    )

    print(
        f"Geometry duplicate wards: "
        f"{geometry_duplicates}"
    )

    if geometry_duplicates != 0:
        raise ValueError(
            "Duplicate Ward_No values found "
            "in geometry dataset."
        )

    # --------------------------------------------------------
    # CHECK WARD COVERAGE
    # --------------------------------------------------------

    print("\nChecking ward coverage...")

    scenario_wards = set(
        scenarios["Ward_No"]
    )

    geometry_wards = set(
        wards["Ward_No"]
    )

    scenario_only = scenario_wards - geometry_wards
    geometry_only = geometry_wards - scenario_wards

    print(
        f"Scenario-only wards: {len(scenario_only)}"
    )

    print(
        f"Geometry-only wards: {len(geometry_only)}"
    )

    if scenario_only or geometry_only:
        raise ValueError(
            "Ward coverage mismatch detected."
        )

    print(
        "Ward coverage validation: PASSED"
    )

    # --------------------------------------------------------
    # CALCULATE NORMALIZED COMPONENTS
    # --------------------------------------------------------

    print("\nPreparing ranking components...")

    scenarios["heat_score"] = min_max_normalize(
        scenarios["estimated_heat_reduction_C"]
    )

    scenarios["emission_score"] = min_max_normalize(
        scenarios["estimated_emission_reduction"]
    )

    scenarios["potential_score"] = min_max_normalize(
        scenarios["intervention_potential"]
    )

    scenarios["combined_score_normalized"] = min_max_normalize(
        scenarios["combined_impact_score"]
    )

    print(
        "Ranking components prepared"
    )

    # --------------------------------------------------------
    # DECISION SCORE
    # --------------------------------------------------------
    #
    # Weighting:
    #   Heat reduction       = 35%
    #   Emission reduction   = 30%
    #   Intervention impact  = 15%
    #   Combined impact      = 20%
    #
    # These weights are transparent and can later be changed
    # by the optimization/decision layer.
    # --------------------------------------------------------

    print("\nCalculating decision scores...")

    scenarios["decision_score"] = (
        0.35 * scenarios["heat_score"]
        + 0.30 * scenarios["emission_score"]
        + 0.15 * scenarios["potential_score"]
        + 0.20 * scenarios["combined_score_normalized"]
    )

    # --------------------------------------------------------
    # RANK ALL SCENARIOS GLOBALLY
    # --------------------------------------------------------

    print(
        "Creating global scenario ranking..."
    )

    scenarios = scenarios.sort_values(
        by=[
            "decision_score",
            "estimated_heat_reduction_C",
            "estimated_emission_reduction",
        ],
        ascending=[
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)

    scenarios["global_rank"] = (
        scenarios.index + 1
    )

    # --------------------------------------------------------
    # RANK INTERVENTIONS WITHIN EACH WARD
    # --------------------------------------------------------

    print(
        "Creating ward-level intervention ranking..."
    )

    scenarios["ward_rank"] = (
        scenarios.groupby("Ward_No")[
            "decision_score"
        ]
        .rank(
            method="first",
            ascending=False
        )
        .astype(int)
    )

    scenarios["recommended"] = (
        scenarios["ward_rank"] == 1
    )

    # --------------------------------------------------------
    # CREATE DECISION LABEL
    # --------------------------------------------------------

    def create_decision_label(rank):

        if rank == 1:
            return "Recommended"

        if rank == 2:
            return "Alternative"

        if rank == 3:
            return "Secondary Alternative"

        return "Lower Priority"

    scenarios["decision_label"] = (
        scenarios["ward_rank"]
        .apply(create_decision_label)
    )

    # --------------------------------------------------------
    # CREATE WARD-WISE BEST INTERVENTION DATA
    # --------------------------------------------------------

    print(
        "Creating ward-level decision summary..."
    )

    best_per_ward = (
        scenarios[
            scenarios["ward_rank"] == 1
        ]
        .copy()
        .sort_values("Ward_No")
    )

    best_per_ward = best_per_ward[
        [
            "Ward_No",
            "Ward_Name",
            "intervention",
            "decision_score",
            "ward_rank",
            "recommended",
            "estimated_heat_reduction_C",
            "estimated_emission_reduction",
            "intervention_potential",
            "combined_impact_score",
        ]
    ]

    # --------------------------------------------------------
    # VALIDATE DECISION DATA
    # --------------------------------------------------------

    print(
        "\nValidating decision ranking dataset..."
    )

    expected_ranked_rows = 272 * 6

    if len(scenarios) != expected_ranked_rows:
        raise ValueError(
            f"Expected {expected_ranked_rows} ranked rows, "
            f"found {len(scenarios)}"
        )

    if best_per_ward["Ward_No"].nunique() != 272:
        raise ValueError(
            "Each ward must have exactly one "
            "top-ranked intervention."
        )

    missing_values = int(
        scenarios[
            [
                "decision_score",
                "global_rank",
                "ward_rank",
            ]
        ]
        .isna()
        .sum()
        .sum()
    )

    if missing_values != 0:
        raise ValueError(
            "Missing ranking values found."
        )

    infinite_values = int(
        np.isinf(
            scenarios[
                [
                    "decision_score",
                    "global_rank",
                    "ward_rank",
                ]
            ]
            .to_numpy(dtype=float)
        ).sum()
    )

    if infinite_values != 0:
        raise ValueError(
            "Infinite ranking values found."
        )

    print(
        "Decision ranking validation: PASSED"
    )

    # --------------------------------------------------------
    # ATTACH GEOMETRY
    # --------------------------------------------------------

    print(
        "\nAttaching ward geometry..."
    )

    geometry_columns = [
        "Ward_No",
        "geometry",
    ]

    ward_geometry = wards[
        geometry_columns
    ].copy()

    ranked_geo = scenarios.merge(
        ward_geometry,
        on="Ward_No",
        how="left",
        validate="many_to_one",
    )

    ranked_geo = gpd.GeoDataFrame(
        ranked_geo,
        geometry="geometry",
        crs=wards.crs,
    )

    missing_geometry = int(
        ranked_geo.geometry.isna().sum()
    )

    invalid_geometry = int(
        (~ranked_geo.geometry.is_valid).sum()
    )

    print(
        f"Missing geometries: {missing_geometry}"
    )

    print(
        f"Invalid geometries: {invalid_geometry}"
    )

    if missing_geometry != 0:
        raise ValueError(
            "Missing ward geometries found."
        )

    if invalid_geometry != 0:
        raise ValueError(
            "Invalid ward geometries found."
        )

    # --------------------------------------------------------
    # SELECT OUTPUT COLUMNS
    # --------------------------------------------------------

    output_columns = [
        "Ward_No",
        "Ward_Name",
        "intervention",
        "intervention_potential",
        "baseline_LST_C",
        "simulated_LST_C",
        "estimated_heat_reduction_C",
        "heat_improvement_percent",
        "baseline_emission_pressure",
        "simulated_emission_pressure",
        "estimated_emission_reduction",
        "emission_improvement_percent",
        "combined_impact_score",
        "heat_score",
        "emission_score",
        "potential_score",
        "combined_score_normalized",
        "decision_score",
        "global_rank",
        "ward_rank",
        "recommended",
        "decision_label",
    ]

    ranked_output = scenarios[
        output_columns
    ].copy()

    # --------------------------------------------------------
    # SAVE CSV
    # --------------------------------------------------------

    print(
        "\nSaving decision ranking CSV..."
    )

    ranked_output.to_csv(
        OUTPUT_CSV,
        index=False,
    )

    print(
        f"CSV saved:\n{OUTPUT_CSV}"
    )

    # --------------------------------------------------------
    # SAVE GEOJSON
    # --------------------------------------------------------

    print(
        "\nSaving decision ranking GeoJSON..."
    )

    geo_output = ranked_geo[
        output_columns + ["geometry"]
    ].copy()

    geo_output.to_file(
        OUTPUT_GEOJSON,
        driver="GeoJSON",
    )

    print(
        f"GeoJSON saved:\n{OUTPUT_GEOJSON}"
    )

    # --------------------------------------------------------
    # CREATE INTERVENTION SUMMARY
    # --------------------------------------------------------

    print(
        "\nCreating intervention ranking summary..."
    )

    intervention_summary = (
        scenarios.groupby("intervention")
        .agg(
            wards=(
                "Ward_No",
                "nunique"
            ),
            average_decision_score=(
                "decision_score",
                "mean"
            ),
            average_heat_reduction_C=(
                "estimated_heat_reduction_C",
                "mean"
            ),
            average_emission_reduction=(
                "estimated_emission_reduction",
                "mean"
            ),
            average_intervention_potential=(
                "intervention_potential",
                "mean"
            ),
            recommended_wards=(
                "recommended",
                "sum"
            ),
        )
        .reset_index()
    )

    intervention_summary[
        "recommended_wards"
    ] = intervention_summary[
        "recommended_wards"
    ].astype(int)

    intervention_summary = (
        intervention_summary.sort_values(
            "average_decision_score",
            ascending=False,
        )
    )

    # --------------------------------------------------------
    # CREATE TOP SCENARIOS
    # --------------------------------------------------------

    top_scenarios = scenarios[
        [
            "Ward_No",
            "Ward_Name",
            "intervention",
            "decision_score",
            "estimated_heat_reduction_C",
            "estimated_emission_reduction",
            "intervention_potential",
            "combined_impact_score",
            "ward_rank",
        ]
    ].head(15)

    top_scenarios_records = (
        top_scenarios
        .round(6)
        .to_dict(
            orient="records"
        )
    )

    # --------------------------------------------------------
    # CREATE SUMMARY JSON
    # --------------------------------------------------------

    summary = {
        "total_wards": int(
            scenarios["Ward_No"].nunique()
        ),
        "total_interventions": int(
            scenarios["intervention"].nunique()
        ),
        "total_scenarios": int(
            len(scenarios)
        ),
        "ranking_method": {
            "heat_reduction_weight": 0.35,
            "emission_reduction_weight": 0.30,
            "intervention_potential_weight": 0.15,
            "combined_impact_weight": 0.20,
        },
        "recommended_intervention_counts": {
            str(row["intervention"]): int(
                row["recommended_wards"]
            )
            for _, row in intervention_summary.iterrows()
        },
        "intervention_summary": (
            intervention_summary
            .round(6)
            .to_dict(
                orient="records"
            )
        ),
        "top_15_scenarios": top_scenarios_records,
    }

    with open(
        OUTPUT_SUMMARY,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=4,
        )

    print(
        f"Summary JSON saved:\n{OUTPUT_SUMMARY}"
    )

    # --------------------------------------------------------
    # DISPLAY TOP 15
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print(
        "TOP 15 HIGHEST-RANKED SCENARIOS"
    )
    print("=" * 65)

    display_columns = [
        "Ward_No",
        "Ward_Name",
        "intervention",
        "decision_score",
        "ward_rank",
        "estimated_heat_reduction_C",
        "estimated_emission_reduction",
    ]

    print(
        scenarios[
            display_columns
        ]
        .head(15)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # DISPLAY RECOMMENDED INTERVENTIONS
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print(
        "WARD-LEVEL RECOMMENDED INTERVENTION SUMMARY"
    )
    print("=" * 65)

    recommended_display = best_per_ward[
        [
            "Ward_No",
            "Ward_Name",
            "intervention",
            "decision_score",
            "estimated_heat_reduction_C",
            "estimated_emission_reduction",
        ]
    ].head(20)

    print(
        recommended_display.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # FINAL VALIDATION
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print(
        "FINAL DECISION RANKING VALIDATION"
    )
    print("=" * 65)

    checks = {
        "272 wards": (
            scenarios["Ward_No"].nunique() == 272
        ),
        "6 interventions": (
            scenarios["intervention"].nunique() == 6
        ),
        "1632 scenarios": (
            len(scenarios) == 1632
        ),
        "No missing ranking values": (
            not ranked_output[
                [
                    "decision_score",
                    "global_rank",
                    "ward_rank",
                ]
            ].isna().any().any()
        ),
        "No infinite ranking values": (
            not np.isinf(
                ranked_output[
                    [
                        "decision_score",
                        "global_rank",
                        "ward_rank",
                    ]
                ]
                .to_numpy(dtype=float)
            ).any()
        ),
        "One recommendation per ward": (
            best_per_ward["Ward_No"].nunique()
            == 272
        ),
        "Geometry available": (
            ranked_geo.geometry.notna().all()
        ),
        "Geometry valid": (
            ranked_geo.geometry.is_valid.all()
        ),
        "CSV exists": OUTPUT_CSV.exists(),
        "GeoJSON exists": OUTPUT_GEOJSON.exists(),
        "Summary exists": OUTPUT_SUMMARY.exists(),
    }

    for check_name, result in checks.items():

        print(
            f"{check_name}: {result}"
        )

    if not all(checks.values()):
        raise ValueError(
            "Decision ranking validation failed."
        )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print(
        "DECISION RANKING ENGINE SUMMARY"
    )
    print("=" * 65)

    print(
        f"Wards: {scenarios['Ward_No'].nunique()}"
    )

    print(
        f"Interventions: "
        f"{scenarios['intervention'].nunique()}"
    )

    print(
        f"Total scenarios: {len(scenarios)}"
    )

    print(
        f"Recommended scenarios: "
        f"{best_per_ward.shape[0]}"
    )

    print("\nIntervention recommendation counts:")

    print(
        intervention_summary[
            [
                "intervention",
                "recommended_wards",
                "average_decision_score",
            ]
        ].to_string(
            index=False
        )
    )

    print("\nOutput files:")

    print(
        OUTPUT_CSV
    )

    print(
        OUTPUT_GEOJSON
    )

    print(
        OUTPUT_SUMMARY
    )

    print("\n" + "=" * 65)
    print(
        "DECISION RANKING ENGINE COMPLETED SUCCESSFULLY"
    )
    print("=" * 65)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()