"""
models/ai_model.py
Decision tree model for crop/livestock recommendation.

Fixes vs original friendly branch:
  - Encoders (soil_type, farm_type) are saved alongside the model in the
    same .pkl bundle so predict() always works after a server restart.
  - Paths come from core.config — no more hardcoded strings.
  - train_and_save() and load_model() are explicit public functions.
  - predict() is a clean callable: give it raw input, get a recommendation.
  - Auto-trains on startup if .pkl is missing (called from app.py lifespan).

Bundle saved as:
    {
        "model":        DecisionTreeClassifier,
        "soil_encoder": LabelEncoder,   # fitted on ['clay','loamy','sandy']
        "farm_encoder": LabelEncoder,   # fitted on ['crop','livestock']
    }
"""

import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

from core.config import settings


# ── Training ──────────────────────────────────────────────────────────────────

def train_and_save() -> dict:
    """
    Reads seed_data.csv, trains a DecisionTreeClassifier, and saves the model
    + encoders as a single bundle to settings.MODEL_PATH.

    Returns the loaded bundle dict so the caller can use it immediately
    without a second disk read.
    """
    df = pd.read_csv(settings.SEED_DATA_PATH)

    # Fit encoders on the full dataset so all known values are covered
    soil_encoder = LabelEncoder().fit(df["soil_type"])
    farm_encoder = LabelEncoder().fit(df["farm_type"])

    df["soil_enc"] = soil_encoder.transform(df["soil_type"])
    df["farm_enc"] = farm_encoder.transform(df["farm_type"])

    X = df[["avg_rainfall", "avg_temp", "soil_enc", "farm_enc"]]
    y = df["recommendation"]

    model = DecisionTreeClassifier(max_depth=5, random_state=42)
    model.fit(X, y)

    bundle = {
        "model": model,
        "soil_encoder": soil_encoder,
        "farm_encoder": farm_encoder,
    }

    settings.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, settings.MODEL_PATH)

    print(f"[ai_model] Trained on {len(df)} rows → saved to {settings.MODEL_PATH}")
    print(f"[ai_model] Classes: {list(model.classes_)}")
    return bundle


# ── Loading ───────────────────────────────────────────────────────────────────

def load_model() -> dict:
    """
    Loads the model bundle from disk.
    If the .pkl doesn't exist, trains and saves it first (auto-train on startup).

    Returns:
        {
            "model":        DecisionTreeClassifier,
            "soil_encoder": LabelEncoder,
            "farm_encoder": LabelEncoder,
        }
    """
    if not settings.MODEL_PATH.exists():
        print("[ai_model] No .pkl found — training now...")
        return train_and_save()

    bundle = joblib.load(settings.MODEL_PATH)
    print(f"[ai_model] Loaded model from {settings.MODEL_PATH}")
    return bundle


# ── Prediction ────────────────────────────────────────────────────────────────

def predict(
    bundle: dict,
    avg_rainfall: float,
    avg_temp: float,
    soil_type: str,
    farm_type: str,
) -> str:
    """
    Predicts the best crop or livestock recommendation from raw input values.

    Args:
        bundle:       The dict returned by load_model() or train_and_save().
        avg_rainfall: Annual rainfall in mm.
        avg_temp:     Average temperature in °C.
        soil_type:    One of 'sandy', 'loamy', 'clay'.
        farm_type:    One of 'crop', 'livestock'.

    Returns:
        Recommendation string e.g. 'maize', 'goat', 'beans'.
        Falls back to 'maize' if an unseen label is passed (safe default).
    """
    model: DecisionTreeClassifier = bundle["model"]
    soil_encoder: LabelEncoder = bundle["soil_encoder"]
    farm_encoder: LabelEncoder = bundle["farm_encoder"]

    # Handle unseen soil/farm labels gracefully
    soil_type = soil_type.lower().strip()
    farm_type = farm_type.lower().strip()

    known_soils = list(soil_encoder.classes_)
    known_farms = list(farm_encoder.classes_)

    if soil_type not in known_soils:
        print(f"[ai_model] Unknown soil '{soil_type}', defaulting to 'loamy'")
        soil_type = "loamy"

    if farm_type not in known_farms:
        print(f"[ai_model] Unknown farm type '{farm_type}', defaulting to 'crop'")
        farm_type = "crop"

    soil_enc = soil_encoder.transform([soil_type])[0]
    farm_enc = farm_encoder.transform([farm_type])[0]

    import pandas as _pd
    X = _pd.DataFrame(
        [[avg_rainfall, avg_temp, soil_enc, farm_enc]],
        columns=["avg_rainfall", "avg_temp", "soil_enc", "farm_enc"],
    )
    prediction = model.predict(X)[0]
    return str(prediction)


# ── Standalone retrain ────────────────────────────────────────────────────────

if __name__ == "__main__":
    train_and_save()