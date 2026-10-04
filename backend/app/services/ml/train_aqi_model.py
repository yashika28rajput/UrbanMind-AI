import os
import json
import pickle
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


# ============================================================
# UrbanMind AI - AQI Prediction Model Training
# ============================================================

TRAIN_FILE = "data/processed/ml/aqi/delhi_aqi_train.csv"
VALIDATION_FILE = "data/processed/ml/aqi/delhi_aqi_validation.csv"
TEST_FILE = "data/processed/ml/aqi/delhi_aqi_test.csv"

MODEL_DIR = "models/aqi"

MODEL_FILE = os.path.join(
    MODEL_DIR,
    "aqi_model.pkl"
)

METADATA_FILE = os.path.join(
    MODEL_DIR,
    "aqi_model_info.json"
)

TARGET = "AQI"


print("=" * 70)
print("UrbanMind AI - AQI Prediction Model Training")
print("=" * 70)


# ============================================================
# 1. CHECK DATASETS
# ============================================================

print("\nChecking AQI ML datasets...")

for name, path in [
    ("Training", TRAIN_FILE),
    ("Validation", VALIDATION_FILE),
    ("Testing", TEST_FILE),
]:

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{name} dataset not found: {path}"
        )

    print(f"{name}: FOUND")


# ============================================================
# 2. LOAD DATA
# ============================================================

print("\nLoading datasets...")

train = pd.read_csv(TRAIN_FILE)
validation = pd.read_csv(VALIDATION_FILE)
test = pd.read_csv(TEST_FILE)

print(f"Training records: {len(train)}")
print(f"Validation records: {len(validation)}")
print(f"Testing records: {len(test)}")


# ============================================================
# 3. TARGET VALIDATION
# ============================================================

print("\nValidating target column...")

for dataset_name, dataset in [
    ("Training", train),
    ("Validation", validation),
    ("Testing", test),
]:

    if TARGET not in dataset.columns:
        raise ValueError(
            f"{TARGET} missing from {dataset_name} dataset"
        )

print("Target validation: PASSED")


# ============================================================
# 4. IDENTIFY FEATURES
# ============================================================

print("\nPreparing ML features...")

excluded_columns = [
    "AQI",
    "AQI_category",
    "location_id",
    "station_name",
    "timestamp_local",
]

feature_columns = [
    column
    for column in train.columns
    if column not in excluded_columns
]


if not feature_columns:
    raise ValueError(
        "No ML features available."
    )


print(
    f"Number of features: {len(feature_columns)}"
)


# ============================================================
# 5. FEATURE CONSISTENCY
# ============================================================

print("\nChecking feature consistency...")

validation_features = [
    column
    for column in validation.columns
    if column not in excluded_columns
]

test_features = [
    column
    for column in test.columns
    if column not in excluded_columns
]

if feature_columns != validation_features:
    raise ValueError(
        "Training and validation features do not match."
    )

if feature_columns != test_features:
    raise ValueError(
        "Training and test features do not match."
    )

print("Feature consistency: PASSED")


# ============================================================
# 6. CREATE X AND y
# ============================================================

print("\nCreating X and y...")

X_train = train[feature_columns].copy()
y_train = train[TARGET].copy()

X_validation = validation[
    feature_columns
].copy()

y_validation = validation[
    TARGET
].copy()

X_test = test[
    feature_columns
].copy()

y_test = test[
    TARGET
].copy()


# ============================================================
# 7. NUMERIC VALIDATION
# ============================================================

print("\nChecking numeric features...")

for column in feature_columns:

    X_train[column] = pd.to_numeric(
        X_train[column],
        errors="coerce"
    )

    X_validation[column] = pd.to_numeric(
        X_validation[column],
        errors="coerce"
    )

    X_test[column] = pd.to_numeric(
        X_test[column],
        errors="coerce"
    )


X_train = X_train.replace(
    [np.inf, -np.inf],
    np.nan
)

X_validation = X_validation.replace(
    [np.inf, -np.inf],
    np.nan
)

X_test = X_test.replace(
    [np.inf, -np.inf],
    np.nan
)


if (
    X_train.isna().sum().sum() > 0
    or X_validation.isna().sum().sum() > 0
    or X_test.isna().sum().sum() > 0
):

    raise ValueError(
        "Missing or invalid numeric feature values detected."
    )


print("Numeric feature validation: PASSED")


# ============================================================
# 8. MODEL EVALUATION FUNCTION
# ============================================================

def evaluate_model(model, X, y):

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

    return {
        "predictions": predictions,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
    }


# ============================================================
# 9. PREPARE MODELS
# ============================================================

print("\n" + "=" * 70)
print("Preparing models...")
print("=" * 70)


models = {

    "Random Forest": RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1
    ),

    "Gradient Boosting": GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=3,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=42
    ),
}


results = {}


# ============================================================
# 10. TRAIN MODELS
# ============================================================

for model_name, model in models.items():

    print("\n" + "=" * 70)
    print(f"Training {model_name}...")
    print("=" * 70)

    model.fit(
        X_train,
        y_train
    )

    print(
        f"{model_name} training completed."
    )

    train_result = evaluate_model(
        model,
        X_train,
        y_train
    )

    validation_result = evaluate_model(
        model,
        X_validation,
        y_validation
    )

    results[model_name] = {
        "model": model,
        "train": train_result,
        "validation": validation_result,
    }

    print("\nTraining Results:")

    print(
        f"MAE : "
        f"{train_result['mae']:.4f}"
    )

    print(
        f"RMSE: "
        f"{train_result['rmse']:.4f}"
    )

    print(
        f"R²  : "
        f"{train_result['r2']:.4f}"
    )

    print("\nValidation Results:")

    print(
        f"MAE : "
        f"{validation_result['mae']:.4f}"
    )

    print(
        f"RMSE: "
        f"{validation_result['rmse']:.4f}"
    )

    print(
        f"R²  : "
        f"{validation_result['r2']:.4f}"
    )


# ============================================================
# 11. MODEL COMPARISON
# ============================================================

print("\n" + "=" * 70)
print("MODEL COMPARISON")
print("=" * 70)


for model_name, result in results.items():

    validation_result = result[
        "validation"
    ]

    print(f"\n{model_name}")

    print(
        f"Validation MAE : "
        f"{validation_result['mae']:.4f}"
    )

    print(
        f"Validation RMSE: "
        f"{validation_result['rmse']:.4f}"
    )

    print(
        f"Validation R²  : "
        f"{validation_result['r2']:.4f}"
    )


# ============================================================
# 12. SELECT BEST MODEL
# ============================================================

best_model_name = min(
    results,
    key=lambda name:
    results[name]["validation"]["rmse"]
)

best_model = results[
    best_model_name
]["model"]


print("\n" + "=" * 70)
print("SELECTED MODEL")
print("=" * 70)

print(
    f"Model: {best_model_name}"
)

print(
    "Selection metric: Validation RMSE"
)


# ============================================================
# 13. TEST EVALUATION
# ============================================================

print(
    "\nEvaluating selected model "
    "on unseen test data..."
)

test_result = evaluate_model(
    best_model,
    X_test,
    y_test
)


print("\nTest Results:")

print(
    f"MAE : "
    f"{test_result['mae']:.4f}"
)

print(
    f"RMSE: "
    f"{test_result['rmse']:.4f}"
)

print(
    f"R²  : "
    f"{test_result['r2']:.4f}"
)


# ============================================================
# 14. FEATURE IMPORTANCE
# ============================================================

print("\nCalculating feature importance...")

if hasattr(
    best_model,
    "feature_importances_"
):

    importance_df = pd.DataFrame({
        "feature": feature_columns,
        "importance":
            best_model.feature_importances_
    })

    importance_df = importance_df.sort_values(
        "importance",
        ascending=False
    ).reset_index(drop=True)

    print("\nTop 15 Important Features:")

    print(
        importance_df.head(15).to_string(
            index=False
        )
    )

else:

    importance_df = pd.DataFrame(
        columns=[
            "feature",
            "importance"
        ]
    )


# ============================================================
# 15. SAVE MODEL
# ============================================================

print("\nSaving trained model...")

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


with open(
    MODEL_FILE,
    "wb"
) as f:

    pickle.dump(
        best_model,
        f
    )


print(
    f"Model saved:\n{MODEL_FILE}"
)


# ============================================================
# 16. SAVE METADATA
# ============================================================

metadata = {

    "model": best_model_name,

    "target": TARGET,

    "features": feature_columns,

    "number_of_features":
        len(feature_columns),

    "training_records":
        len(train),

    "validation_records":
        len(validation),

    "test_records":
        len(test),

    "validation_metrics": {

        "mae":
            float(
                results[
                    best_model_name
                ]["validation"]["mae"]
            ),

        "rmse":
            float(
                results[
                    best_model_name
                ]["validation"]["rmse"]
            ),

        "r2":
            float(
                results[
                    best_model_name
                ]["validation"]["r2"]
            ),
    },

    "test_metrics": {

        "mae":
            float(
                test_result["mae"]
            ),

        "rmse":
            float(
                test_result["rmse"]
            ),

        "r2":
            float(
                test_result["r2"]
            ),
    },

    "feature_importance": {

        row["feature"]:
            float(row["importance"])

        for _, row
        in importance_df.iterrows()
    },
}


with open(
    METADATA_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        metadata,
        f,
        indent=4
    )


print(
    f"Model metadata saved:\n"
    f"{METADATA_FILE}"
)


# ============================================================
# 17. FINAL VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL MODEL VALIDATION")
print("=" * 70)


model_exists = os.path.exists(
    MODEL_FILE
)

metadata_exists = os.path.exists(
    METADATA_FILE
)

predictions_finite = np.isfinite(
    test_result["predictions"]
).all()

features_valid = (
    len(feature_columns) > 0
)

target_excluded = (
    TARGET not in feature_columns
)


print(
    f"Training data available: "
    f"{len(train) > 0}"
)

print(
    f"Validation data available: "
    f"{len(validation) > 0}"
)

print(
    f"Test data available: "
    f"{len(test) > 0}"
)

print(
    f"Features available: "
    f"{features_valid}"
)

print(
    f"Target excluded from features: "
    f"{target_excluded}"
)

print(
    f"Model trained: "
    f"{best_model is not None}"
)

print(
    f"Test predictions finite: "
    f"{predictions_finite}"
)

print(
    f"Model file exists: "
    f"{model_exists}"
)

print(
    f"Metadata file exists: "
    f"{metadata_exists}"
)


if not all([
    len(train) > 0,
    len(validation) > 0,
    len(test) > 0,
    features_valid,
    target_excluded,
    predictions_finite,
    model_exists,
    metadata_exists,
]):

    raise ValueError(
        "AQI model validation failed."
    )


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("AQI MODEL TRAINING SUMMARY")
print("=" * 70)

print(
    f"Training records : {len(train)}"
)

print(
    f"Validation records: {len(validation)}"
)

print(
    f"Test records      : {len(test)}"
)

print(
    f"Features          : "
    f"{len(feature_columns)}"
)

print(
    f"Target            : {TARGET}"
)

print(
    f"Selected model    : "
    f"{best_model_name}"
)

print(
    f"Test MAE          : "
    f"{test_result['mae']:.4f}"
)

print(
    f"Test RMSE         : "
    f"{test_result['rmse']:.4f}"
)

print(
    f"Test R²           : "
    f"{test_result['r2']:.4f}"
)

print("\nModel output files:")

print(MODEL_FILE)
print(METADATA_FILE)

print(
    "\nAQI MODEL TRAINING COMPLETED SUCCESSFULLY"
)

print("=" * 70)