import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)


print("=" * 60)
print("UrbanMind AI - Urban Heat Prediction Model Training")
print("=" * 60)


# ============================================================
# Paths
# ============================================================

BASE_PATH = "data/processed/ml"

TRAIN_PATH = (
    f"{BASE_PATH}/urban_heat_train.csv"
)

VALIDATION_PATH = (
    f"{BASE_PATH}/urban_heat_validation.csv"
)

TEST_PATH = (
    f"{BASE_PATH}/urban_heat_test.csv"
)

MODEL_DIR = "models/urban_heat"

BEST_MODEL_PATH = (
    f"{MODEL_DIR}/urban_heat_model.pkl"
)

MODEL_INFO_PATH = (
    f"{MODEL_DIR}/urban_heat_model_info.json"
)


TARGET = "mean_LST_C"

ID_COLUMNS = [
    "Ward_No",
    "Ward_Name"
]


# ============================================================
# Check Files
# ============================================================

print("\nChecking ML datasets...")

for name, path in {
    "Training": TRAIN_PATH,
    "Validation": VALIDATION_PATH,
    "Testing": TEST_PATH
}.items():

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"{name} dataset not found:\n{path}"
        )

    print(f"{name}: FOUND")


# ============================================================
# Load Data
# ============================================================

print("\nLoading datasets...")

train_df = pd.read_csv(TRAIN_PATH)

validation_df = pd.read_csv(
    VALIDATION_PATH
)

test_df = pd.read_csv(
    TEST_PATH
)


print(
    f"Training records: "
    f"{len(train_df)}"
)

print(
    f"Validation records: "
    f"{len(validation_df)}"
)

print(
    f"Testing records: "
    f"{len(test_df)}"
)


# ============================================================
# Validate Target
# ============================================================

print("\nValidating target column...")

for name, df in {
    "Training": train_df,
    "Validation": validation_df,
    "Testing": test_df
}.items():

    if TARGET not in df.columns:

        raise ValueError(
            f"{TARGET} missing from {name} dataset."
        )

    if df[TARGET].isna().any():

        raise ValueError(
            f"Missing target values in {name}."
        )


print("Target validation: PASSED")


# ============================================================
# Determine Features
# ============================================================

print("\nPreparing ML features...")

FEATURE_COLUMNS = [
    column
    for column in train_df.columns
    if column not in ID_COLUMNS
    and column != TARGET
]


print(
    f"Number of features: "
    f"{len(FEATURE_COLUMNS)}"
)


# ============================================================
# Target Leakage Protection
# ============================================================

if TARGET in FEATURE_COLUMNS:

    raise ValueError(
        "Target leakage detected: "
        "mean_LST_C is present as a feature."
    )


# ============================================================
# Feature Consistency
# ============================================================

print(
    "\nChecking feature consistency..."
)

for name, df in {
    "Validation": validation_df,
    "Testing": test_df
}.items():

    missing_features = [
        column
        for column in FEATURE_COLUMNS
        if column not in df.columns
    ]

    if missing_features:

        raise ValueError(
            f"{name} dataset is missing features: "
            f"{missing_features}"
        )


print(
    "Feature consistency: PASSED"
)


# ============================================================
# Prepare X and y
# ============================================================

print("\nCreating X and y...")

X_train = train_df[
    FEATURE_COLUMNS
].copy()

y_train = train_df[
    TARGET
].copy()


X_validation = validation_df[
    FEATURE_COLUMNS
].copy()

y_validation = validation_df[
    TARGET
].copy()


X_test = test_df[
    FEATURE_COLUMNS
].copy()

y_test = test_df[
    TARGET
].copy()


# ============================================================
# Numeric Validation
# ============================================================

print(
    "\nChecking numeric features..."
)

for name, X in {
    "Training": X_train,
    "Validation": X_validation,
    "Testing": X_test
}.items():

    if not all(
        pd.api.types.is_numeric_dtype(
            X[column]
        )
        for column in X.columns
    ):

        raise ValueError(
            f"Non-numeric feature found in {name}."
        )

    if X.isna().sum().sum() != 0:

        raise ValueError(
            f"Missing feature values in {name}."
        )

    if np.isinf(
        X.to_numpy()
    ).any():

        raise ValueError(
            f"Infinite feature values in {name}."
        )


print(
    "Numeric feature validation: PASSED"
)


# ============================================================
# Model Evaluation Function
# ============================================================

def evaluate_model(
    model,
    X,
    y,
    dataset_name
):

    predictions = model.predict(X)

    mae = mean_absolute_error(
        y,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y,
            predictions
        )
    )

    r2 = r2_score(
        y,
        predictions
    )

    print(
        f"\n{dataset_name} Results:"
    )

    print(
        f"MAE : {mae:.4f} °C"
    )

    print(
        f"RMSE: {rmse:.4f} °C"
    )

    print(
        f"R²  : {r2:.4f}"
    )

    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "R2": float(r2)
    }


# ============================================================
# Define Models
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "Preparing models..."
)

print(
    "=" * 60
)


models = {

    "Random Forest": RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    ),

    "Gradient Boosting": GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42
    )
}


# ============================================================
# Train Models
# ============================================================

results = {}


for model_name, model in models.items():

    print(
        "\n" + "=" * 60
    )

    print(
        f"Training {model_name}..."
    )

    print(
        "=" * 60
    )

    model.fit(
        X_train,
        y_train
    )

    print(
        f"{model_name} training completed."
    )


    # --------------------------------------------------------
    # Training Evaluation
    # --------------------------------------------------------

    train_results = evaluate_model(
        model,
        X_train,
        y_train,
        "Training"
    )


    # --------------------------------------------------------
    # Validation Evaluation
    # --------------------------------------------------------

    validation_results = evaluate_model(
        model,
        X_validation,
        y_validation,
        "Validation"
    )


    results[model_name] = {
        "training": train_results,
        "validation": validation_results
    }


# ============================================================
# Model Comparison
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "MODEL COMPARISON"
)

print(
    "=" * 60
)


for model_name, result in results.items():

    validation = result[
        "validation"
    ]

    print(
        f"\n{model_name}"
    )

    print(
        f"Validation MAE : "
        f"{validation['MAE']:.4f} °C"
    )

    print(
        f"Validation RMSE: "
        f"{validation['RMSE']:.4f} °C"
    )

    print(
        f"Validation R²  : "
        f"{validation['R2']:.4f}"
    )


# ============================================================
# Select Model
# ============================================================

# Select based on lowest validation RMSE.

best_model_name = min(
    results,
    key=lambda name:
        results[name]["validation"]["RMSE"]
)


best_model = models[
    best_model_name
]


print(
    "\n" + "=" * 60
)

print(
    "SELECTED MODEL"
)

print(
    "=" * 60
)

print(
    f"Model: {best_model_name}"
)

print(
    "Selection metric: "
    "Validation RMSE"
)


# ============================================================
# Final Test Evaluation
# ============================================================

print(
    "\nEvaluating selected model "
    "on unseen test data..."
)


test_results = evaluate_model(
    best_model,
    X_test,
    y_test,
    "Test"
)


# ============================================================
# Feature Importance
# ============================================================

print(
    "\nCalculating feature importance..."
)


if hasattr(
    best_model,
    "feature_importances_"
):

    feature_importance = pd.DataFrame({

        "feature":
            FEATURE_COLUMNS,

        "importance":
            best_model.feature_importances_

    })


    feature_importance = (
        feature_importance
        .sort_values(
            "importance",
            ascending=False
        )
        .reset_index(drop=True)
    )


    print(
        "\nTop 15 Important Features:"
    )

    print(
        feature_importance
        .head(15)
        .to_string(index=False)
    )


else:

    feature_importance = pd.DataFrame(
        columns=[
            "feature",
            "importance"
        ]
    )


# ============================================================
# Create Model Directory
# ============================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# ============================================================
# Save Best Model
# ============================================================

print(
    "\nSaving trained model..."
)


joblib.dump(
    best_model,
    BEST_MODEL_PATH
)


print(
    f"Model saved:\n"
    f"{BEST_MODEL_PATH}"
)


# ============================================================
# Save Model Metadata
# ============================================================

model_info = {

    "project":
        "UrbanMind AI",

    "task":
        "Urban Heat Prediction",

    "target":
        TARGET,

    "selected_model":
        best_model_name,

    "number_of_features":
        len(FEATURE_COLUMNS),

    "features":
        FEATURE_COLUMNS,

    "training_records":
        len(train_df),

    "validation_records":
        len(validation_df),

    "test_records":
        len(test_df),

    "validation_metrics":
        results[
            best_model_name
        ]["validation"],

    "test_metrics":
        test_results,

    "feature_importance":
        feature_importance
        .to_dict(
            orient="records"
        )
}


with open(
    MODEL_INFO_PATH,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        model_info,
        file,
        indent=4
    )


print(
    f"Model metadata saved:\n"
    f"{MODEL_INFO_PATH}"
)


# ============================================================
# Final Summary
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "URBAN HEAT MODEL TRAINING SUMMARY"
)

print(
    "=" * 60
)

print(
    f"Training records : "
    f"{len(train_df)}"
)

print(
    f"Validation records: "
    f"{len(validation_df)}"
)

print(
    f"Test records      : "
    f"{len(test_df)}"
)

print(
    f"Features          : "
    f"{len(FEATURE_COLUMNS)}"
)

print(
    f"Target            : "
    f"{TARGET}"
)

print(
    f"Selected model    : "
    f"{best_model_name}"
)

print(
    f"Test MAE          : "
    f"{test_results['MAE']:.4f} °C"
)

print(
    f"Test RMSE         : "
    f"{test_results['RMSE']:.4f} °C"
)

print(
    f"Test R²           : "
    f"{test_results['R2']:.4f}"
)


# ============================================================
# Final Validation
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "FINAL MODEL VALIDATION"
)

print(
    "=" * 60
)


checks = {

    "Training data available":
        len(train_df) > 0,

    "Validation data available":
        len(validation_df) > 0,

    "Test data available":
        len(test_df) > 0,

    "Features available":
        len(FEATURE_COLUMNS) == 45,

    "Target excluded from features":
        TARGET not in FEATURE_COLUMNS,

    "Model trained":
        best_model is not None,

    "Test predictions finite":
        np.isfinite(
            best_model.predict(X_test)
        ).all(),

    "Model file exists":
        os.path.exists(
            BEST_MODEL_PATH
        ),

    "Metadata file exists":
        os.path.exists(
            MODEL_INFO_PATH
        )
}


for name, result in checks.items():

    print(
        f"{name}: {result}"
    )


if not all(checks.values()):

    raise ValueError(
        "Model validation failed."
    )


print(
    "\nURBAN HEAT MODEL "
    "TRAINING COMPLETED SUCCESSFULLY"
)

print(
    "=" * 60
)