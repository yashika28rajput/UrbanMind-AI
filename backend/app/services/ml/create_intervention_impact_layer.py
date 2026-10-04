import os
import json
import numpy as np
import pandas as pd


# ================================================================
# UrbanMind AI - Intervention Impact Layer
# ================================================================

print("=" * 70)
print("UrbanMind AI - Intervention Impact Layer")
print("=" * 70)


# ------------------------------------------------
# Paths
# ------------------------------------------------

ENVIRONMENT_FILE = (
    "data/processed/ml/environmental/"
    "delhi_ward_environmental_risk.csv"
)

HEALTH_FILE = (
    "data/processed/ml/health/"
    "delhi_ward_health_impact.csv"
)

OUTPUT_DIR = "data/processed/ml/interventions"

OUTPUT_CSV = os.path.join(
    OUTPUT_DIR,
    "delhi_ward_intervention_impacts.csv"
)

OUTPUT_SUMMARY = os.path.join(
    OUTPUT_DIR,
    "intervention_impact_summary.json"
)


# ------------------------------------------------
# Required columns
# ------------------------------------------------

ENV_COLUMNS = [
    "Ward_No",
    "Ward_Name",
    "final_AQI",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score",
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C",
    "air_pollution_mitigation_potential",
    "urban_intervention_potential"
]

HEALTH_COLUMNS = [
    "TOT_P",
    "children_percent",
    "health_exposure_score"
]


# ------------------------------------------------
# Interventions
# ------------------------------------------------

INTERVENTIONS = [
    "green_cover",
    "urban_forest",
    "roadside_greening",
    "cool_roof",
    "water_restoration",
    "sustainable_mobility"
]


# ------------------------------------------------
# Check files
# ------------------------------------------------

print("\nChecking required files...")

if not os.path.exists(ENVIRONMENT_FILE):
    raise FileNotFoundError(
        f"Environmental risk file not found:\n{ENVIRONMENT_FILE}"
    )

if not os.path.exists(HEALTH_FILE):
    raise FileNotFoundError(
        f"Health impact file not found:\n{HEALTH_FILE}"
    )

print("Environmental risk layer: FOUND")
print("Health impact layer: FOUND")


# ------------------------------------------------
# Load data
# ------------------------------------------------

print("\nLoading environmental data...")

environment = pd.read_csv(ENVIRONMENT_FILE)

print(f"Environmental records: {len(environment)}")


print("\nLoading health data...")

health = pd.read_csv(HEALTH_FILE)

print(f"Health records: {len(health)}")


# ------------------------------------------------
# Column validation
# ------------------------------------------------

print("\nChecking required columns...")

missing_env = [
    col for col in ENV_COLUMNS
    if col not in environment.columns
]

missing_health = [
    col for col in HEALTH_COLUMNS
    if col not in health.columns
]

if missing_env:
    raise ValueError(
        f"Missing environmental columns: {missing_env}"
    )

if missing_health:
    raise ValueError(
        f"Missing health columns: {missing_health}"
    )

print("Environmental columns: PASSED")
print("Health columns: PASSED")


# ------------------------------------------------
# Normalize Ward IDs
# ------------------------------------------------

print("\nNormalizing Ward IDs...")

environment["Ward_No"] = pd.to_numeric(
    environment["Ward_No"],
    errors="coerce"
)

health["Ward_No"] = pd.to_numeric(
    health["Ward_No"],
    errors="coerce"
)

if environment["Ward_No"].isna().any():
    raise ValueError("Invalid Ward_No in environmental data.")

if health["Ward_No"].isna().any():
    raise ValueError("Invalid Ward_No in health data.")

environment["Ward_No"] = (
    environment["Ward_No"].astype(int)
)

health["Ward_No"] = (
    health["Ward_No"].astype(int)
)

print("Ward ID normalization: PASSED")


# ------------------------------------------------
# Duplicate validation
# ------------------------------------------------

print("\nChecking duplicate wards...")

env_duplicates = environment["Ward_No"].duplicated().sum()
health_duplicates = health["Ward_No"].duplicated().sum()

print(f"Environmental duplicates: {env_duplicates}")
print(f"Health duplicates: {health_duplicates}")

if env_duplicates > 0:
    raise ValueError("Duplicate wards in environmental data.")

if health_duplicates > 0:
    raise ValueError("Duplicate wards in health data.")

print("Duplicate validation: PASSED")


# ------------------------------------------------
# Merge environmental + health
# ------------------------------------------------

print("\nMerging environmental and health data...")

data = environment.merge(
    health[
        [
            "Ward_No",
            "TOT_P",
            "children_percent",
            "health_exposure_score"
        ]
    ],
    on="Ward_No",
    how="inner"
)

print(f"Records after merge: {len(data)}")

if len(data) != 272:
    raise ValueError(
        f"Expected 272 wards but found {len(data)}"
    )

print("Environmental + health merge: PASSED")


# ------------------------------------------------
# Numeric validation
# ------------------------------------------------

print("\nValidating numeric indicators...")

numeric_columns = [
    "final_AQI",
    "AQI_risk_index",
    "heat_risk_index",
    "emission_risk_index",
    "traffic_risk_index",
    "vegetation_risk_index",
    "environmental_risk_score",
    "mean_LST_C",
    "predicted_LST_C",
    "heat_anomaly_C",
    "air_pollution_mitigation_potential",
    "urban_intervention_potential",
    "TOT_P",
    "children_percent",
    "health_exposure_score"
]

for col in numeric_columns:
    data[col] = pd.to_numeric(
        data[col],
        errors="coerce"
    )

missing_values = data[numeric_columns].isna().sum()

if missing_values.sum() > 0:
    print(missing_values[missing_values > 0])
    raise ValueError(
        "Missing numeric values found."
    )

print("Numeric validation: PASSED")


# ------------------------------------------------
# Create intervention scenarios
# ------------------------------------------------

print("\nCreating intervention scenarios...")

scenario_rows = []

for _, row in data.iterrows():

    for intervention in INTERVENTIONS:

        # ----------------------------------------
        # Base values
        # ----------------------------------------

        aqI = float(row["final_AQI"])
        lst = float(row["predicted_LST_C"])

        heat_risk = float(
            row["heat_risk_index"]
        )

        emission_risk = float(
            row["emission_risk_index"]
        )

        traffic_risk = float(
            row["traffic_risk_index"]
        )

        vegetation_risk = float(
            row["vegetation_risk_index"]
        )

        air_pollution = float(
            row["air_pollution_mitigation_potential"]
        )

        intervention_potential = float(
            row["urban_intervention_potential"]
        )

        # ----------------------------------------
        # Intervention impact assumptions
        # ----------------------------------------

        if intervention == "green_cover":

            heat_reduction = (
                1.5
                * (0.5 + vegetation_risk)
            )

            emission_reduction = (
                0.15
                * (0.5 + air_pollution)
            )

            aqi_improvement = (
                4.0
                * (0.5 + air_pollution)
            )

        elif intervention == "urban_forest":

            heat_reduction = (
                2.0
                * (0.5 + vegetation_risk)
            )

            emission_reduction = (
                0.20
                * (0.5 + air_pollution)
            )

            aqi_improvement = (
                5.0
                * (0.5 + air_pollution)
            )

        elif intervention == "roadside_greening":

            heat_reduction = (
                1.2
                * (0.5 + vegetation_risk)
            )

            emission_reduction = (
                0.25
                * (0.5 + traffic_risk)
            )

            aqi_improvement = (
                3.0
                * (0.5 + air_pollution)
            )

        elif intervention == "cool_roof":

            heat_reduction = (
                1.8
                * (0.5 + heat_risk)
            )

            emission_reduction = 0.05

            aqi_improvement = 1.0

        elif intervention == "water_restoration":

            heat_reduction = (
                1.6
                * (0.5 + heat_risk)
            )

            emission_reduction = 0.05

            aqi_improvement = 1.5

        elif intervention == "sustainable_mobility":

            heat_reduction = (
                0.7
                * (0.5 + traffic_risk)
            )

            emission_reduction = (
                0.35
                * (0.5 + traffic_risk)
            )

            aqi_improvement = (
                6.0
                * (0.5 + traffic_risk)
            )

        else:
            raise ValueError(
                f"Unknown intervention: {intervention}"
            )

        # ----------------------------------------
        # Bound impacts
        # ----------------------------------------

        heat_reduction = max(
            0,
            min(heat_reduction, 5)
        )

        emission_reduction = max(
            0,
            min(emission_reduction, 1)
        )

        aqi_improvement = max(
            0,
            min(aqi_improvement, aqI * 0.50)
        )

        # ----------------------------------------
        # Projected values
        # ----------------------------------------

        projected_heat = max(
            0,
            lst - heat_reduction
        )

        projected_aqi = max(
            0,
            aqI - aqi_improvement
        )

        # ----------------------------------------
        # Health impact estimate
        # ----------------------------------------

        population = float(
            row["TOT_P"]
        )

        children_percent = float(
            row["children_percent"]
        )

        health_exposure = float(
            row["health_exposure_score"]
        )

        exposure_reduction = (
            health_exposure
            * (
                0.03
                + 0.02 * (
                    heat_reduction / 5
                )
                + 0.02 * (
                    aqi_improvement / max(aqI, 1)
                )
            )
        )

        population_benefited = (
            population
            * min(
                exposure_reduction / 100,
                0.25
            )
        )

        child_population = (
            population
            * children_percent
            / 100
        )

        # ----------------------------------------
        # Overall impact score
        # ----------------------------------------

        heat_component = min(
            heat_reduction / 5,
            1
        )

        emission_component = min(
            emission_reduction,
            1
        )

        aqi_component = min(
            aqi_improvement / max(aqI, 1),
            1
        )

        health_component = min(
            exposure_reduction / 100,
            1
        )

        impact_score = (
            0.30 * heat_component
            + 0.25 * emission_component
            + 0.25 * aqi_component
            + 0.20 * health_component
        )

        scenario_rows.append(
            {
                "Ward_No": int(row["Ward_No"]),
                "Ward_Name": row["Ward_Name"],
                "intervention": intervention,

                "baseline_AQI": aqI,
                "projected_AQI": projected_aqi,
                "estimated_AQI_improvement":
                    aqi_improvement,

                "baseline_LST_C": lst,
                "projected_LST_C": projected_heat,
                "estimated_heat_reduction_C":
                    heat_reduction,

                "estimated_emission_reduction":
                    emission_reduction,

                "population": population,
                "child_population":
                    child_population,

                "health_exposure_score":
                    health_exposure,

                "estimated_exposure_reduction":
                    exposure_reduction,

                "estimated_population_benefited":
                    population_benefited,

                "intervention_potential":
                    intervention_potential,

                "impact_score":
                    impact_score
            }
        )


scenarios = pd.DataFrame(scenario_rows)

print(
    f"Scenarios created: {len(scenarios)}"
)


# ------------------------------------------------
# Validate scenario count
# ------------------------------------------------

print("\nValidating scenario coverage...")

expected_scenarios = 272 * 6

if len(scenarios) != expected_scenarios:
    raise ValueError(
        f"Expected {expected_scenarios} scenarios "
        f"but found {len(scenarios)}"
    )

duplicate_pairs = scenarios.duplicated(
    subset=["Ward_No", "intervention"]
).sum()

if duplicate_pairs > 0:
    raise ValueError(
        f"Duplicate ward-intervention pairs: "
        f"{duplicate_pairs}"
    )

print("272 wards: PASSED")
print("6 interventions: PASSED")
print("1632 scenarios: PASSED")
print("Ward-intervention uniqueness: PASSED")


# ------------------------------------------------
# Validate numeric values
# ------------------------------------------------

print("\nValidating scenario values...")

impact_columns = [
    "baseline_AQI",
    "projected_AQI",
    "estimated_AQI_improvement",
    "baseline_LST_C",
    "projected_LST_C",
    "estimated_heat_reduction_C",
    "estimated_emission_reduction",
    "population",
    "child_population",
    "health_exposure_score",
    "estimated_exposure_reduction",
    "estimated_population_benefited",
    "intervention_potential",
    "impact_score"
]

for col in impact_columns:

    if scenarios[col].isna().any():
        raise ValueError(
            f"Missing values in {col}"
        )

    if not np.isfinite(
        scenarios[col].to_numpy()
    ).all():
        raise ValueError(
            f"Infinite values in {col}"
        )

print("Missing values: 0")
print("Infinite values: 0")
print("Numeric validation: PASSED")


# ------------------------------------------------
# Rank scenarios
# ------------------------------------------------

print("\nRanking intervention impacts...")

scenarios = scenarios.sort_values(
    [
        "Ward_No",
        "impact_score"
    ],
    ascending=[True, False]
)

scenarios["intervention_rank"] = (
    scenarios
    .groupby("Ward_No")
    ["impact_score"]
    .rank(
        method="first",
        ascending=False
    )
    .astype(int)
)


# ------------------------------------------------
# Save
# ------------------------------------------------

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

print("\nSaving intervention impact dataset...")

scenarios.to_csv(
    OUTPUT_CSV,
    index=False
)

print(f"CSV saved:\n{OUTPUT_CSV}")


# ------------------------------------------------
# Summary
# ------------------------------------------------

summary = {
    "wards": int(
        scenarios["Ward_No"].nunique()
    ),
    "interventions": len(INTERVENTIONS),
    "total_scenarios": len(scenarios),
    "mean_impact_score": float(
        scenarios["impact_score"].mean()
    ),
    "max_impact_score": float(
        scenarios["impact_score"].max()
    ),
    "min_impact_score": float(
        scenarios["impact_score"].min()
    ),
    "intervention_average_impact": (
        scenarios
        .groupby("intervention")["impact_score"]
        .mean()
        .sort_values(
            ascending=False
        )
        .to_dict()
    )
}

with open(
    OUTPUT_SUMMARY,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        summary,
        f,
        indent=4
    )

print(
    f"Summary saved:\n{OUTPUT_SUMMARY}"
)


# ------------------------------------------------
# Sample output
# ------------------------------------------------

print("\n" + "=" * 70)
print("TOP INTERVENTION IMPACT SCENARIOS")
print("=" * 70)

print(
    scenarios[
        [
            "Ward_No",
            "Ward_Name",
            "intervention",
            "impact_score",
            "estimated_heat_reduction_C",
            "estimated_AQI_improvement",
            "estimated_emission_reduction",
            "estimated_population_benefited"
        ]
    ]
    .sort_values(
        "impact_score",
        ascending=False
    )
    .head(15)
    .to_string(index=False)
)


# ------------------------------------------------
# Final validation
# ------------------------------------------------

print("\n" + "=" * 70)
print("FINAL INTERVENTION IMPACT VALIDATION")
print("=" * 70)

print(
    f"272 wards: "
    f"{scenarios['Ward_No'].nunique() == 272}"
)

print(
    f"6 interventions: "
    f"{scenarios['intervention'].nunique() == 6}"
)

print(
    f"1632 scenarios: "
    f"{len(scenarios) == 1632}"
)

print(
    f"No missing values: "
    f"{not scenarios[impact_columns].isna().any().any()}"
)

print(
    f"No infinite values: "
    f"{np.isfinite(scenarios[impact_columns].to_numpy()).all()}"
)

print(
    f"CSV exists: "
    f"{os.path.exists(OUTPUT_CSV)}"
)

print(
    f"Summary exists: "
    f"{os.path.exists(OUTPUT_SUMMARY)}"
)


print("\n" + "=" * 70)
print("INTERVENTION IMPACT LAYER COMPLETED SUCCESSFULLY")
print("=" * 70)