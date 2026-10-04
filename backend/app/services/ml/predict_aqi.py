import os
import json
import joblib
import numpy as np
import pandas as pd


# ============================================================
# UrbanMind AI - AQI Prediction Pipeline
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../..")
)

ML_DATASET_PATH = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "ml",
    "aqi",
    "delhi_aqi_ml_dataset.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "aqi",
    "aqi_model.pkl"
)

MODEL_INFO_PATH = os.path.join(
    BASE_DIR,
    "models",
    "aqi",
    "aqi_model_info.json"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "processed",
    "ml",
    "aqi"
)

PREDICTION_PATH = os.path.join(
    OUTPUT_DIR,
    "delhi_aqi_predictions.csv"
)

SUMMARY_PATH = os.path.join(
    OUTPUT_DIR,
    "aqi_prediction_summary.json"
)


# ============================================================
# AQI CATEGORY FUNCTION
# ============================================================

def get_aqi_category(aqi):

    if aqi <= 50:
        return "Good"

    elif aqi <= 100:
        return "Satisfactory"

    elif aqi <= 200:
        return "Moderate"

    elif aqi <= 300:
        return "Poor"

    elif aqi <= 400:
        return "Very Poor"

    else:
        return "Severe"


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("UrbanMind AI - AQI Prediction Pipeline")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. CHECK REQUIRED FILES
    # --------------------------------------------------------

    print("\nChecking required files...")

    if not os.path.exists(ML_DATASET_PATH):
        raise FileNotFoundError(
            f"AQI ML dataset not found:\n{ML_DATASET_PATH}"
        )

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"AQI model not found:\n{MODEL_PATH}"
        )

    if not os.path.exists(MODEL_INFO_PATH):
        raise FileNotFoundError(
            f"Model metadata not found:\n{MODEL_INFO_PATH}"
        )

    print("AQI ML dataset: FOUND")
    print("Trained model: FOUND")
    print("Model metadata: FOUND")

    # --------------------------------------------------------
    # 2. LOAD DATASET
    # --------------------------------------------------------

    print("\nLoading AQI ML dataset...")

    df = pd.read_csv(ML_DATASET_PATH)

    print(f"Records: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    if df.empty:
        raise ValueError("AQI dataset is empty.")

    # --------------------------------------------------------
    # 3. LOAD MODEL
    # --------------------------------------------------------

    print("\nLoading trained AQI model...")

    model = joblib.load(MODEL_PATH)

    print("Trained AQI model loaded successfully")

    # --------------------------------------------------------
    # 4. LOAD MODEL METADATA
    # --------------------------------------------------------

    print("\nLoading model metadata...")

    with open(MODEL_INFO_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    model_name = metadata.get(
        "selected_model",
        metadata.get("model", "Unknown")
    )

    expected_features = metadata.get("features")

    print(f"Model: {model_name}")

    # --------------------------------------------------------
    # 5. IDENTIFY FEATURES
    # --------------------------------------------------------

    print("\nPreparing prediction features...")

    target_column = "AQI"

    if target_column not in df.columns:
        raise ValueError("Target column 'AQI' not found.")

    # Prefer metadata feature list if available
    if isinstance(expected_features, list):

        feature_columns = expected_features

        missing_features = [
            col for col in feature_columns
            if col not in df.columns
        ]

        if missing_features:
            raise ValueError(
                f"Missing model features: {missing_features}"
            )

    else:

        # Fallback: use model's stored feature names
        if hasattr(model, "feature_names_in_"):

            feature_columns = list(model.feature_names_in_)

        else:

            feature_columns = [
                col for col in df.columns
                if col != target_column
                and col not in [
                    "station_name",
                    "timestamp_local",
                    "timestamp_utc"
                ]
            ]

    print(f"Number of features: {len(feature_columns)}")

    # --------------------------------------------------------
    # 6. NUMERIC VALIDATION
    # --------------------------------------------------------

    print("\nChecking numeric features...")

    for column in feature_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    missing_values = df[feature_columns].isna().sum().sum()

    if missing_values > 0:
        raise ValueError(
            f"Missing feature values found: {missing_values}"
        )

    infinite_values = np.isinf(
        df[feature_columns].to_numpy(dtype=float)
    ).sum()

    if infinite_values > 0:
        raise ValueError(
            f"Infinite feature values found: {infinite_values}"
        )

    print("Numeric validation: PASSED")

    # --------------------------------------------------------
    # 7. CREATE FEATURE MATRIX
    # --------------------------------------------------------

    X = df[feature_columns].copy()

    # --------------------------------------------------------
    # 8. GENERATE PREDICTIONS
    # --------------------------------------------------------

    print("\nGenerating AQI predictions...")

    predictions = model.predict(X)

    predictions = np.asarray(
        predictions,
        dtype=float
    )

    if len(predictions) != len(df):
        raise ValueError(
            "Prediction count does not match dataset records."
        )

    if not np.isfinite(predictions).all():
        raise ValueError(
            "Infinite or invalid predictions detected."
        )

    print("AQI predictions generated successfully")

    # --------------------------------------------------------
    # 9. CREATE OUTPUT DATASET
    # --------------------------------------------------------

    output = pd.DataFrame()

    # Preserve useful identifying columns if available

    preferred_columns = [
        "location_id",
        "station_name",
        "sensor_id",
        "timestamp_utc",
        "timestamp_local"
    ]

    for column in preferred_columns:

        if column in df.columns:
            output[column] = df[column]

    # Actual AQI

    output["actual_AQI"] = df[target_column].values

    # Predicted AQI

    output["predicted_AQI"] = predictions

    # Prediction error

    output["prediction_error"] = (
        output["predicted_AQI"]
        - output["actual_AQI"]
    )

    # Absolute error

    output["absolute_error"] = (
        output["prediction_error"]
        .abs()
    )

    # AQI category

    output["AQI_category"] = (
        output["predicted_AQI"]
        .apply(get_aqi_category)
    )

    # --------------------------------------------------------
    # 10. VALIDATE OUTPUT
    # --------------------------------------------------------

    print("\nValidating prediction output...")

    if len(output) != len(df):
        raise ValueError(
            "Output record count mismatch."
        )

    if output["predicted_AQI"].isna().any():
        raise ValueError(
            "Missing AQI predictions found."
        )

    if np.isinf(
        output["predicted_AQI"].to_numpy()
    ).any():

        raise ValueError(
            "Infinite AQI predictions found."
        )

    if output["AQI_category"].isna().any():
        raise ValueError(
            "Missing AQI categories found."
        )

    print(f"Records: {len(output)}")
    print("Missing predictions: 0")
    print("Infinite predictions: 0")
    print("AQI categories created: PASSED")

    # --------------------------------------------------------
    # 11. CALCULATE SUMMARY METRICS
    # --------------------------------------------------------

    mae = float(
        output["absolute_error"].mean()
    )

    rmse = float(
        np.sqrt(
            np.mean(
                output["prediction_error"] ** 2
            )
        )
    )

    actual_mean = float(
        output["actual_AQI"].mean()
    )

    predicted_mean = float(
        output["predicted_AQI"].mean()
    )

    actual_min = float(
        output["actual_AQI"].min()
    )

    actual_max = float(
        output["actual_AQI"].max()
    )

    predicted_min = float(
        output["predicted_AQI"].min()
    )

    predicted_max = float(
        output["predicted_AQI"].max()
    )

    # --------------------------------------------------------
    # 12. AQI CATEGORY DISTRIBUTION
    # --------------------------------------------------------

    category_distribution = (
        output["AQI_category"]
        .value_counts()
        .to_dict()
    )

    # Convert numpy integers to Python integers

    category_distribution = {
        str(key): int(value)
        for key, value in category_distribution.items()
    }

    # --------------------------------------------------------
    # 13. SAVE PREDICTIONS
    # --------------------------------------------------------

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print("\nSaving AQI predictions...")

    output.to_csv(
        PREDICTION_PATH,
        index=False
    )

    print("Predictions saved:")
    print(PREDICTION_PATH)

    # --------------------------------------------------------
    # 14. CREATE SUMMARY JSON
    # --------------------------------------------------------

    summary = {

        "model": model_name,

        "records_processed": int(len(output)),

        "features": int(len(feature_columns)),

        "target": "AQI",

        "actual_AQI": {
            "minimum": actual_min,
            "maximum": actual_max,
            "mean": actual_mean
        },

        "predicted_AQI": {
            "minimum": predicted_min,
            "maximum": predicted_max,
            "mean": predicted_mean
        },

        "prediction_metrics": {
            "MAE": mae,
            "RMSE": rmse
        },

        "AQI_category_distribution":
            category_distribution,

        "output_file":
            PREDICTION_PATH

    }

    with open(
        SUMMARY_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            indent=4
        )

    print("Summary saved:")
    print(SUMMARY_PATH)

    # --------------------------------------------------------
    # 15. DISPLAY SAMPLE PREDICTIONS
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("SAMPLE AQI PREDICTIONS")
    print("=" * 70)

    display_columns = [
        column
        for column in [
            "station_name",
            "timestamp_local",
            "actual_AQI",
            "predicted_AQI",
            "absolute_error",
            "AQI_category"
        ]
        if column in output.columns
    ]

    print(
        output[display_columns]
        .head(10)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # 16. CATEGORY DISTRIBUTION
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("AQI CATEGORY DISTRIBUTION")
    print("=" * 70)

    for category, count in category_distribution.items():

        percentage = (
            count / len(output)
        ) * 100

        print(
            f"{category}: "
            f"{count} records "
            f"({percentage:.2f}%)"
        )

    # --------------------------------------------------------
    # 17. FINAL SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("AQI PREDICTION SUMMARY")
    print("=" * 70)

    print(f"Records processed : {len(output)}")
    print(f"Model             : {model_name}")
    print(f"Features          : {len(feature_columns)}")
    print(f"Actual mean AQI   : {actual_mean:.2f}")
    print(f"Predicted mean AQI: {predicted_mean:.2f}")
    print(f"Prediction MAE    : {mae:.4f}")
    print(f"Prediction RMSE   : {rmse:.4f}")

    print("\nOutput files:")
    print(PREDICTION_PATH)
    print(SUMMARY_PATH)

    print("\n" + "=" * 70)
    print("AQI PREDICTION PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)