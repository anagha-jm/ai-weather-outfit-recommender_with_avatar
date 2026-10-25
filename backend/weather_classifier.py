"""Load and apply the trained weather classifier."""

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_MODEL_PATH = PROJECT_ROOT / "model" / "weather_classifier.pkl"
WEATHER_FEATURE_COLUMNS = ["min_temp", "max_temp", "rainfall", "max_speed"]
WEATHER_CATEGORIES = {"hot", "cold", "rainy"}


def load_weather_classifier(model_path: Path = WEATHER_MODEL_PATH) -> Any:
    if not model_path.is_file():
        raise RuntimeError(
            f"Weather classifier not found at {model_path}. "
            "Train it with train_weather_classifier.py before starting the backend."
        )

    try:
        classifier = joblib.load(model_path)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load weather classifier at {model_path}: {exc}"
        ) from exc

    feature_names = getattr(classifier, "feature_names_in_", None)
    if feature_names is None or list(feature_names) != WEATHER_FEATURE_COLUMNS:
        raise RuntimeError(
            f"Weather classifier at {model_path} must accept features in this order: "
            f"{WEATHER_FEATURE_COLUMNS}; found {feature_names!r}."
        )

    classes = getattr(classifier, "classes_", None)
    if classes is None or set(classes) != WEATHER_CATEGORIES:
        raise RuntimeError(
            f"Weather classifier at {model_path} must predict exactly "
            f"{sorted(WEATHER_CATEGORIES)}; found {classes!r}."
        )
    return classifier


weather_classifier = load_weather_classifier()


def predict_weather_category(weather: dict[str, Any]) -> str:
    """Predict a category from the forecast feature contract used in training."""
    if not isinstance(weather, dict):
        raise ValueError("Weather forecast must be a dictionary.")

    missing_features = [
        column for column in WEATHER_FEATURE_COLUMNS if column not in weather
    ]
    if missing_features:
        raise ValueError(f"Weather forecast is missing features: {missing_features}")

    try:
        values = [float(weather[column]) for column in WEATHER_FEATURE_COLUMNS]
    except (TypeError, ValueError) as exc:
        raise ValueError("Weather forecast features must be numeric.") from exc
    if not np.isfinite(values).all():
        raise ValueError("Weather forecast features must be finite numbers.")

    row = pd.DataFrame([values], columns=WEATHER_FEATURE_COLUMNS)
    prediction = str(weather_classifier.predict(row)[0])
    if prediction not in WEATHER_CATEGORIES:
        raise RuntimeError(
            f"Weather classifier returned unsupported category {prediction!r}."
        )
    return prediction
