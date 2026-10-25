"""Train and evaluate a weather-category classifier from the project CSV."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedGroupKFold,
    cross_validate,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text


RANDOM_SEED = 42
FEATURE_COLUMNS = ["min_temp", "max_temp", "rainfall", "max_speed"]
TARGET_COLUMN = "weather_category"
CLASS_NAMES = ["cold", "hot", "rainy"]
CV_FOLDS = 5
TEST_FRACTION = 0.2


def load_dataset(dataset_path: Path) -> pd.DataFrame:
    """Load the CSV and reject malformed values rather than dropping rows."""
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset file was not found: {dataset_path}")

    try:
        data = pd.read_csv(dataset_path)
    except pd.errors.ParserError as exc:
        raise ValueError(f"Could not parse dataset CSV: {exc}") from exc

    required_columns = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing_columns = sorted(required_columns.difference(data.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")

    extra_columns = sorted(set(data.columns).difference(required_columns))
    if extra_columns:
        print(f"Ignoring columns outside the feature/target contract: {extra_columns}")

    data = data[FEATURE_COLUMNS + [TARGET_COLUMN]].copy()
    for column in FEATURE_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    missing_counts = data.isna().sum()
    if missing_counts.any():
        raise ValueError(
            "Missing or non-numeric values found; no rows were removed:\n"
            f"{missing_counts[missing_counts > 0].to_string()}"
        )

    if not np.isfinite(data[FEATURE_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError("Non-finite feature values found; no rows were removed.")

    unexpected_labels = sorted(set(data[TARGET_COLUMN]) - set(CLASS_NAMES))
    if unexpected_labels:
        raise ValueError(f"Unexpected target labels found: {unexpected_labels}")
    absent_labels = sorted(set(CLASS_NAMES) - set(data[TARGET_COLUMN]))
    if absent_labels:
        raise ValueError(f"Required target classes are absent: {absent_labels}")

    invalid_order = data["min_temp"] > data["max_temp"]
    if invalid_order.any():
        raise ValueError(
            f"{int(invalid_order.sum())} rows have min_temp greater than max_temp; "
            "no rows were removed."
        )
    for column in ("rainfall", "max_speed"):
        negative_values = data[column] < 0
        if negative_values.any():
            raise ValueError(
                f"{int(negative_values.sum())} rows have negative {column}; "
                "no rows were removed."
            )

    return data


def report_dataset_checks(data: pd.DataFrame) -> None:
    """Print data-quality checks and flag unusually large physical values."""
    print(f"Dataset shape: {data.shape[0]} rows x {data.shape[1]} required columns")
    print(f"Columns: {list(data.columns)}")
    print("Data types:")
    print(data.dtypes.to_string())
    print(f"Missing values: {int(data.isna().sum().sum())}")
    print(f"Exact duplicate rows: {int(data.duplicated().sum())}")

    feature_duplicates = data.duplicated(subset=FEATURE_COLUMNS, keep=False)
    conflicting_groups = (
        data.loc[feature_duplicates]
        .groupby(FEATURE_COLUMNS, dropna=False)[TARGET_COLUMN]
        .nunique()
        .gt(1)
    )
    print(f"Repeated feature vectors: {int(data.duplicated(FEATURE_COLUMNS).sum())}")
    print(f"Repeated feature vectors with conflicting labels: {int(conflicting_groups.sum())}")
    print("No rows are deleted by this script.")

    counts = data[TARGET_COLUMN].value_counts().reindex(CLASS_NAMES, fill_value=0)
    proportions = counts / len(data)
    print("Class distribution:")
    for label in CLASS_NAMES:
        print(f"  {label}: {counts[label]} ({proportions[label]:.1%})")
    imbalance_ratio = counts.max() / counts.min()
    print(
        "Class balance: "
        f"{'balanced' if imbalance_ratio <= 1.1 else 'imbalanced'} "
        f"(largest/smallest class ratio {imbalance_ratio:.2f})"
    )

    print("Feature ranges (units assumed: Celsius, mm/day, km/h):")
    print(data[FEATURE_COLUMNS].agg(["min", "max"]).to_string())

    broad_sanity_bounds = {
        "min_temp": (-90, 60),
        "max_temp": (-90, 60),
        "rainfall": (0, 2000),
        "max_speed": (0, 400),
    }
    unusual_values: dict[str, int] = {}
    for column, (lower, upper) in broad_sanity_bounds.items():
        outside = ~data[column].between(lower, upper, inclusive="both")
        if outside.any():
            unusual_values[column] = int(outside.sum())
    if unusual_values:
        print(
            "WARNING: Values outside broad physical sanity bounds "
            f"(rows retained): {unusual_values}"
        )
    else:
        print("Physical sanity checks: no values outside broad bounds; temperatures ordered.")


def feature_groups(features: pd.DataFrame) -> np.ndarray:
    """Give identical measurement vectors a shared group ID for splitting."""
    return pd.MultiIndex.from_frame(features).factorize(sort=False)[0]


def make_pipeline(classifier: Any) -> Pipeline:
    return Pipeline([("classifier", classifier)])


def cross_validation_summary(
    name: str,
    estimator: Pipeline,
    features: pd.DataFrame,
    target: pd.Series,
    cv_splits: list[tuple[np.ndarray, np.ndarray]],
) -> dict[str, Any]:
    scores = cross_validate(
        estimator,
        features,
        target,
        cv=cv_splits,
        scoring={"macro_f1": "f1_macro", "accuracy": "accuracy"},
        return_train_score=True,
        n_jobs=-1,
    )
    return {
        "name": name,
        "estimator": estimator,
        "mean_f1": float(scores["test_macro_f1"].mean()),
        "std_f1": float(scores["test_macro_f1"].std()),
        "mean_accuracy": float(scores["test_accuracy"].mean()),
        "mean_train_f1": float(scores["train_macro_f1"].mean()),
        "tie_priority": 99,
    }


def main() -> int:
    project_dir = Path(__file__).resolve().parent
    dataset_path = project_dir / "data" / "weather_classification_data_1500.csv"
    model_path = project_dir / "model" / "weather_classifier.pkl"

    try:
        data = load_dataset(dataset_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 1

    print(f"Dataset: {dataset_path}")
    report_dataset_checks(data)
    features = data[FEATURE_COLUMNS]
    target = data[TARGET_COLUMN]

    # A shallow full-data tree is used only to inspect label structure, not as
    # validation or as a candidate for model selection.
    diagnostic_tree = DecisionTreeClassifier(max_depth=2, random_state=RANDOM_SEED)
    diagnostic_tree.fit(features, target)
    diagnostic_accuracy = diagnostic_tree.score(features, target)
    print(
        "\nLabel-generation diagnostic (in-sample only): "
        f"a depth-2 decision tree reproduces {diagnostic_accuracy:.1%} of labels."
    )
    if diagnostic_accuracy == 1.0:
        print(
            "WARNING: The labels are exactly separable by two feature thresholds. "
            "This strongly suggests rule-generated labels; the CSV has no provenance "
            "to prove its origin. This is not evidence of real-world accuracy."
        )
    print(export_text(diagnostic_tree, feature_names=FEATURE_COLUMNS, decimals=2))

    groups = feature_groups(features)
    splitter = StratifiedGroupKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )
    outer_train_idx, test_idx = next(splitter.split(features, target, groups))
    X_train, X_test = features.iloc[outer_train_idx], features.iloc[test_idx]
    y_train, y_test = target.iloc[outer_train_idx], target.iloc[test_idx]
    train_groups, test_groups = groups[outer_train_idx], groups[test_idx]
    overlap = set(train_groups).intersection(test_groups)
    if overlap:
        raise RuntimeError(f"Identical feature groups crossed the split: {len(overlap)}")

    print(
        f"Training rows: {len(X_train)}; testing rows: {len(X_test)} "
        f"(grouped, stratified holdout)"
    )
    print(f"Identical feature groups across train/test: {len(overlap)}")
    print(f"Training class counts:\n{y_train.value_counts().reindex(CLASS_NAMES).to_string()}")
    print(f"Testing class counts:\n{y_test.value_counts().reindex(CLASS_NAMES).to_string()}")

    train_class_counts = y_train.value_counts()
    if train_class_counts.min() < CV_FOLDS:
        raise ValueError(
            f"Each training class needs at least {CV_FOLDS} rows for stratified "
            "cross-validation."
        )

    train_splitter = StratifiedGroupKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )
    cv_splits = list(train_splitter.split(X_train, y_train, train_groups))

    baseline = cross_validation_summary(
        "Most-frequent baseline",
        make_pipeline(DummyClassifier(strategy="most_frequent")),
        X_train,
        y_train,
        cv_splits,
    )
    baseline["tie_priority"] = 99
    logistic = cross_validation_summary(
        "Logistic regression",
        Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(max_iter=2000, random_state=RANDOM_SEED),
                ),
            ]
        ),
        X_train,
        y_train,
        cv_splits,
    )
    logistic["tie_priority"] = 0
    comparison: list[dict[str, Any]] = [baseline, logistic]

    decision_tree_search = GridSearchCV(
        make_pipeline(DecisionTreeClassifier(random_state=RANDOM_SEED)),
        {
            "classifier__max_depth": [2, 3, 5, 8, None],
            "classifier__min_samples_leaf": [1, 2, 5],
        },
        scoring={"macro_f1": "f1_macro", "accuracy": "accuracy"},
        cv=cv_splits,
        n_jobs=-1,
        return_train_score=True,
        refit="macro_f1",
    )
    random_forest_search = GridSearchCV(
        make_pipeline(RandomForestClassifier(random_state=RANDOM_SEED)),
        {
            "classifier__n_estimators": [100, 250],
            "classifier__max_depth": [None, 8, 16],
            "classifier__min_samples_leaf": [1, 2, 4],
        },
        scoring={"macro_f1": "f1_macro", "accuracy": "accuracy"},
        cv=cv_splits,
        n_jobs=-1,
        return_train_score=True,
        refit="macro_f1",
    )

    for name, search, tie_priority in (
        ("Decision tree (tuned)", decision_tree_search, 1),
        ("Random forest (tuned)", random_forest_search, 2),
    ):
        search.fit(X_train, y_train)
        best_index = search.best_index_
        comparison.append(
            {
                "name": name,
                "estimator": search.best_estimator_,
                "mean_f1": float(
                    search.cv_results_["mean_test_macro_f1"][best_index]
                ),
                "std_f1": float(search.cv_results_["std_test_macro_f1"][best_index]),
                "mean_accuracy": float(
                    search.cv_results_["mean_test_accuracy"][best_index]
                ),
                "mean_train_f1": float(
                    search.cv_results_["mean_train_macro_f1"][best_index]
                ),
                "tie_priority": tie_priority,
                "best_params": search.best_params_,
            }
        )

    print("\nTraining-only cross-validation comparison (stratified grouped 5-fold):")
    for result in comparison:
        print(
            f"  {result['name']}: macro-F1 "
            f"{result['mean_f1']:.3f} +/- {result['std_f1']:.3f}; "
            f"accuracy {result['mean_accuracy']:.3f}; "
            f"mean train macro-F1 {result['mean_train_f1']:.3f}"
        )
        if "best_params" in result:
            print(f"    selected parameters: {result['best_params']}")

    best_cv_score = max(result["mean_f1"] for result in comparison)
    tied_candidates = [
        result
        for result in comparison
        if best_cv_score - result["mean_f1"] <= 1e-12
    ]
    selected = min(tied_candidates, key=lambda result: result["tie_priority"])
    final_model = selected["estimator"]
    final_model.fit(X_train, y_train)
    print(
        f"\nSelected by training CV macro-F1: {selected['name']} "
        f"(CV macro-F1 {selected['mean_f1']:.3f})."
    )

    train_validation_gap = selected["mean_train_f1"] - selected["mean_f1"]
    print(f"Mean train-CV minus validation-CV macro-F1 gap: {train_validation_gap:.3f}")
    if train_validation_gap > 0.05:
        print("Overfitting check: possible overfitting; training scores exceed CV scores.")
    else:
        print("Overfitting check: no large train/CV macro-F1 gap detected.")

    predictions = final_model.predict(X_test)
    print("\nUntouched test-set evaluation:")
    print(f"Accuracy: {accuracy_score(y_test, predictions):.3f}")
    print(
        "Per-class precision, recall, F1, and support:\n"
        + classification_report(
            y_test,
            predictions,
            labels=CLASS_NAMES,
            target_names=CLASS_NAMES,
            zero_division=0,
            digits=3,
        )
    )
    matrix = confusion_matrix(y_test, predictions, labels=CLASS_NAMES)
    print("Confusion matrix (rows=true, columns=predicted; order cold, hot, rainy):")
    print(pd.DataFrame(matrix, index=CLASS_NAMES, columns=CLASS_NAMES).to_string())

    errors_by_class = matrix.sum(axis=1) - matrix.diagonal()
    if errors_by_class.sum() == 0:
        print("Misclassification review: no test examples were misclassified.")
    else:
        class_error_counts = dict(zip(CLASS_NAMES, errors_by_class.tolist()))
        most_missed = max(class_error_counts, key=class_error_counts.get)
        print(
            f"Misclassifications by true class: {class_error_counts}; "
            f"most frequently misclassified: {most_missed}."
        )
        error_pairs = [
            (int(matrix[row, column]), CLASS_NAMES[row], CLASS_NAMES[column])
            for row in range(len(CLASS_NAMES))
            for column in range(len(CLASS_NAMES))
            if row != column and matrix[row, column] > 0
        ]
        error_pairs.sort(reverse=True)
        print(f"Most frequent true-to-predicted error pairs: {error_pairs}")

    print(
        "\nReliability limitation: the dataset contains no documented source, "
        "timestamps, or location identifiers. Its exact threshold-like labels "
        "make this a label-reproduction exercise, not proof of real-world weather "
        "classification. No genuine historical labels were available for external "
        "validation."
    )

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, model_path)
    reloaded_model = joblib.load(model_path)
    sample = X_test.iloc[: min(5, len(X_test))]
    if not np.array_equal(reloaded_model.predict(sample), final_model.predict(sample)):
        raise RuntimeError("Saved model predictions differ after reloading.")
    print(f"Saved and reload-verified model: {model_path}")
    print(f"Prediction input feature order: {FEATURE_COLUMNS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
