import os
import json
import joblib
import numpy as np
import pandas as pd


print("=" * 60)
print("UrbanMind AI - Urban Heat Prediction Pipeline")
print("=" * 60)


# ============================================================
# PATHS
# ============================================================

DATA_PATH = (
    "data/processed/ml/"
    "urban_heat_ml_dataset.csv"
)

MODEL_PATH = (
    "models/urban_heat/"
    "urban_heat_model.pkl"
)

MODEL_INFO_PATH = (
    "models/urban_heat/"
    "urban_heat_model_info.json"
)

OUTPUT_DIR = (
    "data/processed/ml/"
)

PREDICTION_CSV = (
    OUTPUT_DIR +
    "urban_heat_predictions.csv"
)

SUMMARY_JSON = (
    OUTPUT_DIR +
    "urban_heat_prediction_summary.json"
)


TARGET = "mean_LST_C"

ID_COLUMNS = [
    "Ward_No",
    "Ward_Name"
]


# ============================================================
# CHECK INPUTS
# ============================================================

print("\nChecking required files...")

required_files = {
    "ML dataset": DATA_PATH,
    "Trained model": MODEL_PATH,
    "Model metadata": MODEL_INFO_PATH
}

for name, path in required_files.items():

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"{name} not found:\n{path}"
        )

    print(f"{name}: FOUND")


# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading ML dataset...")

df = pd.read_csv(DATA_PATH)

print(
    f"Records: {len(df)}"
)

print(
    f"Columns: {len(df.columns)}"
)


# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading trained model...")

model = joblib.load(
    MODEL_PATH
)

print(
    "Trained model loaded successfully"
)


# ============================================================
# LOAD MODEL METADATA
# ============================================================

print(
    "\nLoading model metadata..."
)

with open(
    MODEL_INFO_PATH,
    "r",
    encoding="utf-8"
) as file:

    model_info = json.load(file)


FEATURE_COLUMNS = model_info[
    "features"
]

MODEL_NAME = model_info[
    "selected_model"
]


print(
    f"Model: {MODEL_NAME}"
)

print(
    f"Expected features: "
    f"{len(FEATURE_COLUMNS)}"
)


# ============================================================
# VALIDATE DATASET
# ============================================================

print(
    "\nValidating prediction dataset..."
)


if TARGET not in df.columns:

    raise ValueError(
        f"Target column '{TARGET}' "
        "not found."
    )


missing_features = [
    column
    for column in FEATURE_COLUMNS
    if column not in df.columns
]


if missing_features:

    raise ValueError(
        "Missing model features:\n"
        f"{missing_features}"
    )


print(
    "Feature validation: PASSED"
)


# ============================================================
# PREPARE FEATURES
# ============================================================

print(
    "\nPreparing prediction features..."
)

X = df[
    FEATURE_COLUMNS
].copy()


# ============================================================
# NUMERIC VALIDATION
# ============================================================

print(
    "Checking numeric features..."
)


for column in FEATURE_COLUMNS:

    X[column] = pd.to_numeric(
        X[column],
        errors="coerce"
    )


missing_count = (
    X.isna()
    .sum()
    .sum()
)


if missing_count > 0:

    raise ValueError(
        f"Missing/non-numeric values "
        f"found: {missing_count}"
    )


infinite_count = np.isinf(
    X.to_numpy()
).sum()


if infinite_count > 0:

    raise ValueError(
        f"Infinite values found: "
        f"{infinite_count}"
    )


print(
    "Numeric validation: PASSED"
)


# ============================================================
# GENERATE PREDICTIONS
# ============================================================

print(
    "\nGenerating urban heat predictions..."
)


predictions = model.predict(X)


if not np.isfinite(
    predictions
).all():

    raise ValueError(
        "Model generated invalid "
        "predictions."
    )


print(
    "Predictions generated successfully"
)


# ============================================================
# ADD PREDICTION COLUMN
# ============================================================

result = df[
    ID_COLUMNS + [TARGET]
].copy()


result[
    "predicted_LST_C"
] = predictions


# ============================================================
# CALCULATE PREDICTION ERROR
# ============================================================

result[
    "prediction_error_C"
] = (
    result["predicted_LST_C"]
    - result[TARGET]
)


result[
    "absolute_error_C"
] = (
    result["prediction_error_C"]
    .abs()
)


# ============================================================
# HEAT RISK CATEGORY
# ============================================================

print(
    "\nCreating heat-risk categories..."
)


def classify_heat_risk(lst):

    if lst < 33:

        return "Low"

    elif lst < 35:

        return "Moderate"

    elif lst < 37:

        return "High"

    else:

        return "Very High"


result[
    "heat_risk_category"
] = result[
    "predicted_LST_C"
].apply(
    classify_heat_risk
)


# ============================================================
# HEAT ANOMALY
# ============================================================

mean_predicted_lst = (
    result[
        "predicted_LST_C"
    ].mean()
)


result[
    "heat_anomaly_C"
] = (
    result[
        "predicted_LST_C"
    ]
    - mean_predicted_lst
)


# ============================================================
# VALIDATE OUTPUT
# ============================================================

print(
    "\nValidating prediction output..."
)


checks = {

    "Correct ward count":
        len(result) == len(df),

    "Unique wards":
        result["Ward_No"].nunique()
        == len(result),

    "No missing predictions":
        result[
            "predicted_LST_C"
        ].isna().sum() == 0,

    "No infinite predictions":
        np.isinf(
            result[
                "predicted_LST_C"
            ].to_numpy()
        ).sum() == 0,

    "Risk category created":
        result[
            "heat_risk_category"
        ].notna().all(),

    "Actual target available":
        result[
            TARGET
        ].notna().all()
}


for name, status in checks.items():

    print(
        f"{name}: {status}"
    )


if not all(
    checks.values()
):

    raise ValueError(
        "Prediction validation failed."
    )


print(
    "Prediction validation: PASSED"
)


# ============================================================
# SORT BY PREDICTED HEAT
# ============================================================

result = result.sort_values(
    "predicted_LST_C",
    ascending=False
).reset_index(
    drop=True
)


# ============================================================
# SAVE PREDICTIONS
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


print(
    "\nSaving ward-level predictions..."
)


result.to_csv(
    PREDICTION_CSV,
    index=False
)


print(
    f"Predictions saved:\n"
    f"{PREDICTION_CSV}"
)


# ============================================================
# CREATE SUMMARY
# ============================================================

summary = {

    "project":
        "UrbanMind AI",

    "task":
        "Urban Heat Prediction",

    "model":
        MODEL_NAME,

    "wards":
        int(len(result)),

    "actual_LST": {

        "minimum":
            float(
                result[
                    TARGET
                ].min()
            ),

        "maximum":
            float(
                result[
                    TARGET
                ].max()
            ),

        "mean":
            float(
                result[
                    TARGET
                ].mean()
            ),

        "median":
            float(
                result[
                    TARGET
                ].median()
            )
    },

    "predicted_LST": {

        "minimum":
            float(
                result[
                    "predicted_LST_C"
                ].min()
            ),

        "maximum":
            float(
                result[
                    "predicted_LST_C"
                ].max()
            ),

        "mean":
            float(
                result[
                    "predicted_LST_C"
                ].mean()
            ),

        "median":
            float(
                result[
                    "predicted_LST_C"
                ].median()
            )
    },

    "heat_risk_distribution":
        result[
            "heat_risk_category"
        ]
        .value_counts()
        .to_dict(),

    "prediction_error": {

        "MAE":
            float(
                result[
                    "absolute_error_C"
                ].mean()
            ),

        "maximum_absolute_error":
            float(
                result[
                    "absolute_error_C"
                ].max()
            )
    }
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
    f"Summary saved:\n"
    f"{SUMMARY_JSON}"
)


# ============================================================
# DISPLAY TOP HOT WARDS
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "TOP 10 PREDICTED HOT WARDS"
)

print(
    "=" * 60
)


display_columns = [
    "Ward_No",
    "Ward_Name",
    TARGET,
    "predicted_LST_C",
    "heat_anomaly_C",
    "heat_risk_category"
]


print(
    result[
        display_columns
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# RISK DISTRIBUTION
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "HEAT RISK DISTRIBUTION"
)

print(
    "=" * 60
)


risk_counts = (
    result[
        "heat_risk_category"
    ]
    .value_counts()
)


for category, count in (
    risk_counts.items()
):

    percentage = (
        count / len(result)
    ) * 100

    print(
        f"{category}: "
        f"{count} wards "
        f"({percentage:.2f}%)"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "URBAN HEAT PREDICTION SUMMARY"
)

print(
    "=" * 60
)

print(
    f"Wards processed: "
    f"{len(result)}"
)

print(
    f"Model: {MODEL_NAME}"
)

print(
    f"Actual mean LST: "
    f"{result[TARGET].mean():.2f} °C"
)

print(
    f"Predicted mean LST: "
    f"{result['predicted_LST_C'].mean():.2f} °C"
)

print(
    f"Prediction MAE: "
    f"{result['absolute_error_C'].mean():.4f} °C"
)

print(
    "\nOutput files:"
)

print(
    PREDICTION_CSV
)

print(
    SUMMARY_JSON
)


print(
    "\n" + "=" * 60
)

print(
    "URBAN HEAT PREDICTION "
    "COMPLETED SUCCESSFULLY"
)

print(
    "=" * 60
)