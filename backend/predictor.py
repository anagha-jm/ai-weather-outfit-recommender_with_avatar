import os
import joblib
import pandas as pd

# Get project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(BASE_DIR, "model", "outfit_model.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "model", "label_encoder.pkl")

# Feature column order — must exactly match train_model.py lines 60-67.
# Do NOT change this without retraining and validating the model.
FEATURE_COLS = ["rainfall", "min_temp", "max_speed", "max_temp"]

# Load model — wrapped to give an actionable error if pkl files are missing
try:
    model = joblib.load(MODEL_PATH)
    encoder = joblib.load(ENCODER_PATH)
except FileNotFoundError as e:
    raise RuntimeError(
        f"Model files not found — run `python train_model.py` from the project root first.\n"
        f"Missing: {e}"
    )


def predict_outfit(weather):
    """
    weather: dict with keys matching FEATURE_COLS
             {"rainfall": ..., "min_temp": ..., "max_speed": ..., "max_temp": ...}
    Returns: predicted outfit label string
    """
    df = pd.DataFrame([{col: weather[col] for col in FEATURE_COLS}])

    prediction = model.predict(df)

    outfit = encoder.inverse_transform(prediction)

    return outfit[0]