import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd


print("=" * 65)
print("UrbanMind AI - Intervention Scenario Engine")
print("=" * 65)


# ============================================================
# PATHS
# ============================================================

INPUT_PATH = (
    "data/processed/ml/"
    "delhi_ward_heat_risk.geojson"
)

POLICY_PATH = (
    "data/processed/policy/"
    "delhi_ward_policy_planning_features.geojson"
)

EMISSION_PATH = (
    "data/processed/emissions/"
    "delhi_ward_emission_features.geojson"
)

OUTPUT_DIR = (
    "data/processed/scenarios/"
)

OUTPUT_GEOJSON = (
    OUTPUT_DIR +
    "delhi_intervention_scenarios.geojson"
)

OUTPUT_CSV = (
    OUTPUT_DIR +
    "delhi_intervention_scenarios.csv"
)

SUMMARY_JSON = (
    OUTPUT_DIR +
    "intervention_scenario_summary.json"
)


# ============================================================
# INTERVENTIONS
# ============================================================

INTERVENTIONS = {
    "green_cover": {
        "potential_column":
            "green_cover_intervention_potential",

        "heat_reduction_factor":
            0.80,

        "emission_reduction_factor":
            0.30
    },

    "urban_forest": {
        "potential_column":
            "urban_forest_potential",

        "heat_reduction_factor":
            1.00,

        "emission_reduction_factor":
            0.35
    },

    "roadside_greening": {
        "potential_column":
            "roadside_greening_potential",

        "heat_reduction_factor":
            0.60,

        "emission_reduction_factor":
            0.25
    },

    "cool_roof": {
        "potential_column":
            "cool_roof_intervention_potential",

        "heat_reduction_factor":
            0.90,

        "emission_reduction_factor":
            0.10
    },

    "water_restoration": {
        "potential_column":
            "water_body_restoration_potential",

        "heat_reduction_factor":
            0.70,

        "emission_reduction_factor":
            0.20
    },

    "sustainable_mobility": {
        "potential_column":
            "sustainable_mobility_potential",

        "heat_reduction_factor":
            0.35,

        "emission_reduction_factor":
            0.80
    }
}


# ============================================================
# CHECK INPUT FILES
# ============================================================

print("\nChecking input datasets...")

required_files = {
    "Heat risk layer":
        INPUT_PATH,

    "Policy features":
        POLICY_PATH,

    "Emission features":
        EMISSION_PATH
}


for name, path in required_files.items():

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )

    print(
        f"{name}: FOUND"
    )


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading heat-risk layer...")

heat = gpd.read_file(
    INPUT_PATH
)

print(
    f"Heat records: {len(heat)}"
)


print("\nLoading policy features...")

policy = gpd.read_file(
    POLICY_PATH
)

print(
    f"Policy records: {len(policy)}"
)


print("\nLoading emission features...")

emission = gpd.read_file(
    EMISSION_PATH
)

print(
    f"Emission records: {len(emission)}"
)


# ============================================================
# NORMALIZE WARD IDs
# ============================================================

print("\nNormalizing Ward IDs...")


for dataframe in [
    heat,
    policy,
    emission
]:

    if "Ward_No" not in dataframe.columns:

        raise ValueError(
            "Ward_No missing from dataset."
        )

    dataframe["Ward_No"] = pd.to_numeric(
        dataframe["Ward_No"],
        errors="coerce"
    )

    if dataframe["Ward_No"].isna().any():

        raise ValueError(
            "Invalid Ward_No found."
        )

    dataframe["Ward_No"] = (
        dataframe["Ward_No"]
        .astype("int64")
    )


print(
    "Ward IDs normalized successfully"
)


# ============================================================
# DUPLICATE VALIDATION
# ============================================================

print("\nChecking duplicate wards...")

for name, dataframe in [
    ("Heat", heat),
    ("Policy", policy),
    ("Emission", emission)
]:

    duplicates = (
        dataframe["Ward_No"]
        .duplicated()
        .sum()
    )

    print(
        f"{name} duplicates: {duplicates}"
    )

    if duplicates != 0:

        raise ValueError(
            f"Duplicate wards found in "
            f"{name} dataset."
        )


# ============================================================
# COVERAGE VALIDATION
# ============================================================

print("\nChecking ward coverage...")

heat_wards = set(
    heat["Ward_No"]
)

policy_wards = set(
    policy["Ward_No"]
)

emission_wards = set(
    emission["Ward_No"]
)


if heat_wards != policy_wards:

    raise ValueError(
        "Heat and policy ward coverage "
        "does not match."
    )


if heat_wards != emission_wards:

    raise ValueError(
        "Heat and emission ward coverage "
        "does not match."
    )


print(
    "Ward coverage validation: PASSED"
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

print(
    "\nChecking required feature columns..."
)


required_policy_columns = [

    "Ward_No",

    "green_cover_intervention_potential",

    "urban_forest_potential",

    "roadside_greening_potential",

    "cool_roof_intervention_potential",

    "water_body_restoration_potential",

    "sustainable_mobility_potential",

    "heat_mitigation_potential",

    "air_pollution_mitigation_potential"
]


required_emission_columns = [

    "Ward_No",

    "emission_pressure_index",

    "traffic_pressure_index",

    "built_pressure_index",

    "heat_pressure_index",

    "vegetation_mitigation_index"
]


required_heat_columns = [

    "Ward_No",

    "Ward_Name",

    "predicted_LST_C",

    "heat_risk_category"
]


for column in required_policy_columns:

    if column not in policy.columns:

        raise ValueError(
            f"Policy column missing: "
            f"{column}"
        )


for column in required_emission_columns:

    if column not in emission.columns:

        raise ValueError(
            f"Emission column missing: "
            f"{column}"
        )


for column in required_heat_columns:

    if column not in heat.columns:

        raise ValueError(
            f"Heat column missing: "
            f"{column}"
        )


print(
    "Required feature validation: PASSED"
)


# ============================================================
# PREPARE POLICY DATA
# ============================================================

policy_columns = (
    required_policy_columns
)

policy_features = policy[
    policy_columns
].copy()


# ============================================================
# PREPARE EMISSION DATA
# ============================================================

emission_features = emission[
    required_emission_columns
].copy()


# ============================================================
# PREPARE HEAT DATA
# ============================================================

heat_features = heat[
    required_heat_columns
].copy()


# ============================================================
# MERGE DATA
# ============================================================

print(
    "\nMerging heat, policy and emission data..."
)


base = heat_features.merge(
    policy_features,
    on="Ward_No",
    how="left"
)


print(
    f"After heat + policy merge: "
    f"{len(base)} wards"
)


base = base.merge(
    emission_features,
    on="Ward_No",
    how="left"
)


print(
    f"After emission merge: "
    f"{len(base)} wards"
)


if len(base) != 272:

    raise ValueError(
        f"Expected 272 wards, "
        f"found {len(base)}"
    )


# ============================================================
# NUMERIC CONVERSION
# ============================================================

print(
    "\nConverting simulation features to numeric..."
)


numeric_columns = [

    "predicted_LST_C",

    "green_cover_intervention_potential",

    "urban_forest_potential",

    "roadside_greening_potential",

    "cool_roof_intervention_potential",

    "water_body_restoration_potential",

    "sustainable_mobility_potential",

    "heat_mitigation_potential",

    "air_pollution_mitigation_potential",

    "emission_pressure_index",

    "traffic_pressure_index",

    "built_pressure_index",

    "heat_pressure_index",

    "vegetation_mitigation_index"
]


for column in numeric_columns:

    base[column] = pd.to_numeric(
        base[column],
        errors="coerce"
    )


missing_numeric = (
    base[numeric_columns]
    .isna()
    .sum()
    .sum()
)


if missing_numeric > 0:

    raise ValueError(
        f"Missing numeric values: "
        f"{missing_numeric}"
    )


infinite_numeric = np.isinf(
    base[numeric_columns]
    .to_numpy()
).sum()


if infinite_numeric > 0:

    raise ValueError(
        f"Infinite numeric values: "
        f"{infinite_numeric}"
    )


# ============================================================
# CLIP POTENTIALS
# ============================================================

potential_columns = [

    "green_cover_intervention_potential",

    "urban_forest_potential",

    "roadside_greening_potential",

    "cool_roof_intervention_potential",

    "water_body_restoration_potential",

    "sustainable_mobility_potential",

    "heat_mitigation_potential",

    "air_pollution_mitigation_potential"
]


for column in potential_columns:

    base[column] = (
        base[column]
        .clip(0, 1)
    )


print(
    "Numeric feature validation: PASSED"
)


# ============================================================
# BASELINE VALUES
# ============================================================

print(
    "\nCreating baseline indicators..."
)


base[
    "baseline_LST_C"
] = base[
    "predicted_LST_C"
]


base[
    "baseline_emission_pressure"
] = base[
    "emission_pressure_index"
]


# ============================================================
# SCENARIO GENERATION
# ============================================================

print(
    "\nGenerating intervention scenarios..."
)


scenario_records = []


for _, row in base.iterrows():

    ward_no = int(
        row["Ward_No"]
    )

    ward_name = row[
        "Ward_Name"
    ]

    baseline_lst = float(
        row["baseline_LST_C"]
    )

    baseline_emission = float(
        row["baseline_emission_pressure"]
    )

    for intervention, config in (
        INTERVENTIONS.items()
    ):

        potential_column = (
            config[
                "potential_column"
            ]
        )

        potential = float(
            row[
                potential_column
            ]
        )

        heat_factor = float(
            config[
                "heat_reduction_factor"
            ]
        )

        emission_factor = float(
            config[
                "emission_reduction_factor"
            ]
        )

        # ----------------------------------------------------
        # SIMULATED HEAT IMPACT
        # ----------------------------------------------------

        estimated_heat_reduction = (
            baseline_lst
            * potential
            * heat_factor
            * 0.05
        )

        simulated_lst = (
            baseline_lst
            - estimated_heat_reduction
        )

        # ----------------------------------------------------
        # SIMULATED EMISSION IMPACT
        # ----------------------------------------------------

        estimated_emission_reduction = (
            baseline_emission
            * potential
            * emission_factor
        )

        simulated_emission = (
            baseline_emission
            - estimated_emission_reduction
        )

        simulated_emission = np.clip(
            simulated_emission,
            0,
            1
        )

        # ----------------------------------------------------
        # IMPROVEMENT PERCENTAGES
        # ----------------------------------------------------

        if baseline_lst != 0:

            heat_improvement_percent = (
                estimated_heat_reduction
                / baseline_lst
            ) * 100

        else:

            heat_improvement_percent = 0


        if baseline_emission != 0:

            emission_improvement_percent = (
                estimated_emission_reduction
                / baseline_emission
            ) * 100

        else:

            emission_improvement_percent = 0


        # ----------------------------------------------------
        # SCENARIO SCORE
        # ----------------------------------------------------

        combined_impact = (
            0.5
            * heat_improvement_percent
            +
            0.5
            * emission_improvement_percent
        )


        scenario_records.append({

            "Ward_No":
                ward_no,

            "Ward_Name":
                ward_name,

            "intervention":
                intervention,

            "intervention_potential":
                potential,

            "baseline_LST_C":
                baseline_lst,

            "simulated_LST_C":
                simulated_lst,

            "estimated_heat_reduction_C":
                estimated_heat_reduction,

            "heat_improvement_percent":
                heat_improvement_percent,

            "baseline_emission_pressure":
                baseline_emission,

            "simulated_emission_pressure":
                simulated_emission,

            "estimated_emission_reduction":
                estimated_emission_reduction,

            "emission_improvement_percent":
                emission_improvement_percent,

            "combined_impact_score":
                combined_impact

        })


scenarios = pd.DataFrame(
    scenario_records
)


print(
    f"Scenarios generated: "
    f"{len(scenarios)}"
)


# ============================================================
# SCENARIO VALIDATION
# ============================================================

print(
    "\nValidating scenario dataset..."
)


expected_scenarios = (
    272 *
    len(INTERVENTIONS)
)


if len(scenarios) != (
    expected_scenarios
):

    raise ValueError(
        f"Expected "
        f"{expected_scenarios} scenarios, "
        f"found {len(scenarios)}"
    )


expected_interventions = set(
    INTERVENTIONS.keys()
)

actual_interventions = set(
    scenarios[
        "intervention"
    ]
)


if (
    expected_interventions
    != actual_interventions
):

    raise ValueError(
        "Intervention coverage failed."
    )


# ============================================================
# NUMERIC VALIDATION
# ============================================================

scenario_numeric_columns = [

    "intervention_potential",

    "baseline_LST_C",

    "simulated_LST_C",

    "estimated_heat_reduction_C",

    "heat_improvement_percent",

    "baseline_emission_pressure",

    "simulated_emission_pressure",

    "estimated_emission_reduction",

    "emission_improvement_percent",

    "combined_impact_score"
]


for column in scenario_numeric_columns:

    scenarios[column] = pd.to_numeric(
        scenarios[column],
        errors="coerce"
    )


if (
    scenarios[
        scenario_numeric_columns
    ]
    .isna()
    .sum()
    .sum()
    > 0
):

    raise ValueError(
        "Missing values found "
        "in scenario outputs."
    )


if np.isinf(
    scenarios[
        scenario_numeric_columns
    ]
    .to_numpy()
).sum() > 0:

    raise ValueError(
        "Infinite values found "
        "in scenario outputs."
    )


# ============================================================
# SCENARIO SUMMARY
# ============================================================

print(
    "\nCreating scenario summary..."
)


intervention_summary = (
    scenarios
    .groupby("intervention")
    .agg(

        wards=(
            "Ward_No",
            "nunique"
        ),

        average_potential=(
            "intervention_potential",
            "mean"
        ),

        average_heat_reduction_C=(
            "estimated_heat_reduction_C",
            "mean"
        ),

        average_heat_improvement_percent=(
            "heat_improvement_percent",
            "mean"
        ),

        average_emission_reduction=(
            "estimated_emission_reduction",
            "mean"
        ),

        average_emission_improvement_percent=(
            "emission_improvement_percent",
            "mean"
        ),

        average_combined_impact=(
            "combined_impact_score",
            "mean"
        )
    )
    .reset_index()
)


intervention_summary = (
    intervention_summary
    .sort_values(
        "average_combined_impact",
        ascending=False
    )
)


print(
    intervention_summary.to_string(
        index=False
    )
)


# ============================================================
# BEST SCENARIO PER WARD
# ============================================================

print(
    "\nCreating ward-level scenario comparison..."
)


best_scenario_per_ward = (
    scenarios
    .sort_values(
        [
            "Ward_No",
            "combined_impact_score"
        ],
        ascending=[
            True,
            False
        ]
    )
    .groupby(
        "Ward_No",
        as_index=False
    )
    .first()
)


print(
    f"Wards with scenario comparison: "
    f"{len(best_scenario_per_ward)}"
)


# ============================================================
# ADD GEOMETRY
# ============================================================

print(
    "\nAttaching ward geometry..."
)


geometry = heat[
    [
        "Ward_No",
        "geometry"
    ]
].copy()


# Keep only one geometry per ward.

geometry = geometry.drop_duplicates(
    subset=["Ward_No"]
)


scenario_geo = scenarios.merge(
    geometry,
    on="Ward_No",
    how="left"
)


scenario_geo = gpd.GeoDataFrame(
    scenario_geo,
    geometry="geometry",
    crs=heat.crs
)


# ============================================================
# GEOMETRY VALIDATION
# ============================================================

missing_geometry = (
    scenario_geo.geometry
    .isna()
    .sum()
)

invalid_geometry = (
    (~scenario_geo.geometry.is_valid)
    .sum()
)


print(
    f"Missing geometries: "
    f"{missing_geometry}"
)

print(
    f"Invalid geometries: "
    f"{invalid_geometry}"
)


if missing_geometry != 0:

    raise ValueError(
        "Missing geometries in scenario layer."
    )


if invalid_geometry != 0:

    raise ValueError(
        "Invalid geometries in scenario layer."
    )


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# SAVE GEOJSON
# ============================================================

print(
    "\nSaving intervention scenario GeoJSON..."
)


scenario_geo.to_file(
    OUTPUT_GEOJSON,
    driver="GeoJSON"
)


print(
    f"GeoJSON saved:\n"
    f"{OUTPUT_GEOJSON}"
)


# ============================================================
# SAVE CSV
# ============================================================

print(
    "\nSaving intervention scenario CSV..."
)


scenarios.to_csv(
    OUTPUT_CSV,
    index=False
)


print(
    f"CSV saved:\n"
    f"{OUTPUT_CSV}"
)


# ============================================================
# SAVE SUMMARY JSON
# ============================================================

summary = {

    "project":
        "UrbanMind AI",

    "dataset":
        "Ward Intervention Scenario Simulation",

    "wards":
        int(
            scenarios[
                "Ward_No"
            ].nunique()
        ),

    "interventions":
        list(
            INTERVENTIONS.keys()
        ),

    "total_scenarios":
        int(
            len(scenarios)
        ),

    "scenario_method":
        "Potential-weighted heuristic simulation",

    "intervention_summary":
        intervention_summary
        .to_dict(
            orient="records"
        )
}


with open(
    SUMMARY_JSON,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        summary,
        file,
        indent=4
    )


print(
    f"Summary JSON saved:\n"
    f"{SUMMARY_JSON}"
)


# ============================================================
# TOP SCENARIOS
# ============================================================

print(
    "\n" + "=" * 65
)

print(
    "TOP 15 HIGHEST-IMPACT SIMULATED SCENARIOS"
)

print(
    "=" * 65
)


top_columns = [

    "Ward_No",

    "Ward_Name",

    "intervention",

    "intervention_potential",

    "estimated_heat_reduction_C",

    "estimated_emission_reduction",

    "combined_impact_score"

]


print(
    scenarios
    .sort_values(
        "combined_impact_score",
        ascending=False
    )
    [top_columns]
    .head(15)
    .to_string(
        index=False
    )
)


# ============================================================
# FINAL VALIDATION
# ============================================================

print(
    "\n" + "=" * 65
)

print(
    "FINAL SCENARIO ENGINE VALIDATION"
)

print(
    "=" * 65
)


final_checks = {

    "272 wards":
        scenarios[
            "Ward_No"
        ].nunique() == 272,

    "6 interventions":
        scenarios[
            "intervention"
        ].nunique()
        == len(INTERVENTIONS),

    "1632 scenarios":
        len(scenarios)
        == 272 * len(INTERVENTIONS),

    "No missing values":
        not scenarios[
            scenario_numeric_columns
        ].isna().any().any(),

    "No infinite values":
        np.isfinite(
            scenarios[
                scenario_numeric_columns
            ].to_numpy()
        ).all(),

    "Geometry available":
        scenario_geo.geometry
        .notna()
        .all(),

    "Geometry valid":
        scenario_geo.geometry
        .is_valid
        .all(),

    "GeoJSON exists":
        os.path.exists(
            OUTPUT_GEOJSON
        ),

    "CSV exists":
        os.path.exists(
            OUTPUT_CSV
        ),

    "Summary exists":
        os.path.exists(
            SUMMARY_JSON
        )
}


for name, status in (
    final_checks.items()
):

    print(
        f"{name}: {status}"
    )


if not all(
    final_checks.values()
):

    raise ValueError(
        "Scenario engine validation failed."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print(
    "\n" + "=" * 65
)

print(
    "INTERVENTION SCENARIO ENGINE SUMMARY"
)

print(
    "=" * 65
)

print(
    f"Wards: "
    f"{scenarios['Ward_No'].nunique()}"
)

print(
    f"Interventions: "
    f"{scenarios['intervention'].nunique()}"
)

print(
    f"Total scenarios: "
    f"{len(scenarios)}"
)

print(
    "\nInterventions simulated:"
)

for intervention in INTERVENTIONS:

    print(
        f"- {intervention}"
    )

print(
    "\nOutput files:"
)

print(
    OUTPUT_GEOJSON
)

print(
    OUTPUT_CSV
)

print(
    SUMMARY_JSON
)


print(
    "\n" + "=" * 65
)

print(
    "INTERVENTION SCENARIO ENGINE "
    "COMPLETED SUCCESSFULLY"
)

print(
    "=" * 65
)