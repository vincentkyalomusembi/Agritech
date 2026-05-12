"""
models/ai_models.py
Decision-tree model for crop/livestock recommendation.

Feature set (v2)
----------------
  avg_rainfall       — annual mean mm
  avg_temp           — annual mean °C
  elevation_m        — metres above sea level
  irrigation         — 0 rainfed | 1 irrigated
  market_price_index — 1–5 (local market demand/price signal)
  soil_enc           — LabelEncoded soil_type
  farm_enc           — LabelEncoded farm_type

outcome column (0/1) in the CSV marks historically failed combinations so
the model learns both what works and what doesn't.

Bundle saved as:
    {
        "model":        RandomForestClassifier,
        "soil_encoder": LabelEncoder,
        "farm_encoder": LabelEncoder,
        "feature_cols": list[str],   # order matters for predict()
    }
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

from core.config import settings


# ── Feature column order — must stay in sync with predict() ──────────────────
# market_price_index is intentionally excluded from model features.
# It reflects local market conditions, not agronomic suitability — including it
# causes the forest to learn spurious correlations (e.g. low MPI → tea because
# all tea-producing counties happen to have high MPI). MPI is returned as
# context in the recommendation payload but does not influence crop prediction.
FEATURE_COLS = [
    "avg_rainfall",
    "avg_temp",
    "elevation_m",
    "irrigation",
    "soil_enc",
    "farm_enc",
]


# ── Training ──────────────────────────────────────────────────────────────────

def train_and_save() -> dict:
    """
    Reads seed_data.csv, trains a RandomForestClassifier, and saves the model
    + encoders as a single bundle to settings.MODEL_PATH.

    Uses outcome column to weight samples:
      outcome=1  → normal weight
      outcome=0  → higher weight (2×) so failures are not ignored

    Returns the bundle dict.
    """
    df = pd.read_csv(settings.SEED_DATA_PATH)

    # ── Validate required columns ─────────────────────────────────────────────
    required = {"soil_type", "farm_type", "avg_rainfall", "avg_temp",
                "elevation_m", "irrigation", "market_price_index",
                "recommendation", "outcome"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"seed_data.csv is missing columns: {missing}\n"
            "Re-run: python -m db.seed or rebuild seed_data.csv."
        )

    # ── Encode categoricals ───────────────────────────────────────────────────
    soil_encoder = LabelEncoder().fit(df["soil_type"])
    farm_encoder = LabelEncoder().fit(df["farm_type"])

    df["soil_enc"] = soil_encoder.transform(df["soil_type"])
    df["farm_enc"] = farm_encoder.transform(df["farm_type"])

    X = df[FEATURE_COLS]
    y = df["recommendation"]

    # Weight failed outcomes 2× so the model learns from counter-examples
    sample_weight = df["outcome"].apply(lambda o: 1.0 if o == 1 else 2.0)

    # RandomForest generalises better than a single tree for the extra features
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=2,
        random_state=42,
    )
    model.fit(X, y, sample_weight=sample_weight)

    bundle = {
        "model":        model,
        "soil_encoder": soil_encoder,
        "farm_encoder": farm_encoder,
        "feature_cols": FEATURE_COLS,
    }

    settings.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, settings.MODEL_PATH)

    print(f"[ai_model] Trained on {len(df)} rows ({df['outcome'].sum():.0f} positive, "
          f"{(1-df['outcome']).sum():.0f} counter-examples)")
    print(f"[ai_model] Classes: {list(model.classes_)}")
    print(f"[ai_model] Saved → {settings.MODEL_PATH}")

    # Feature importance summary
    importance = sorted(
        zip(FEATURE_COLS, model.feature_importances_),
        key=lambda x: x[1], reverse=True,
    )
    print("[ai_model] Feature importances:")
    for feat, imp in importance:
        bar = "█" * int(imp * 40)
        print(f"  {feat:<22} {imp:.3f}  {bar}")

    return bundle


# ── Loading ───────────────────────────────────────────────────────────────────

def load_model() -> dict:
    """
    Loads the bundle from disk, auto-training if the .pkl is missing
    or was built with the old feature set (missing feature_cols key).
    """
    needs_retrain = True

    if settings.MODEL_PATH.exists():
        bundle = joblib.load(settings.MODEL_PATH)
        # If bundle was trained without the new features, retrain
        if "feature_cols" in bundle and bundle["feature_cols"] == FEATURE_COLS:
            print(f"[ai_model] Loaded model from {settings.MODEL_PATH}")
            needs_retrain = False
        else:
            print("[ai_model] Stale model detected (missing new features) — retraining...")

    if needs_retrain:
        print("[ai_model] Training model...")
        bundle = train_and_save()

    return bundle


# ── Prediction ────────────────────────────────────────────────────────────────

def predict(
    bundle: dict,
    avg_rainfall: float,
    avg_temp: float,
    soil_type: str,
    farm_type: str,
    elevation_m: float = 1000,
    irrigation: int = 0,
    market_price_index: int = 3,
) -> str:
    """
    Predicts the best crop or livestock recommendation.

    Args:
        bundle:             Model bundle from load_model() / train_and_save().
        avg_rainfall:       Annual rainfall mm.
        avg_temp:           Average temperature °C.
        soil_type:          'sandy' | 'loamy' | 'clay' | 'peaty'
        farm_type:          'crop' | 'livestock'
        elevation_m:        Metres above sea level (default 1000m = Kenyan mean).
        irrigation:         0=rainfed, 1=irrigated.
        market_price_index: 1–5 local market demand score.

    Returns:
        Recommendation string e.g. 'maize', 'dairy_cow'.
        Falls back gracefully on unseen label inputs.
    """
    model         = bundle["model"]
    soil_encoder  = bundle["soil_encoder"]
    farm_encoder  = bundle["farm_encoder"]

    soil_type = soil_type.lower().strip()
    farm_type = farm_type.lower().strip()

    known_soils = list(soil_encoder.classes_)
    known_farms = list(farm_encoder.classes_)

    if soil_type not in known_soils:
        print(f"[ai_model] Unknown soil '{soil_type}', defaulting to 'loamy'")
        soil_type = "loamy"

    if farm_type not in known_farms:
        print(f"[ai_model] Unknown farm_type '{farm_type}', defaulting to 'crop'")
        farm_type = "crop"

    soil_enc = soil_encoder.transform([soil_type])[0]
    farm_enc = farm_encoder.transform([farm_type])[0]

    X = pd.DataFrame(
        [[avg_rainfall, avg_temp, elevation_m, irrigation,
          soil_enc, farm_enc]],
        columns=FEATURE_COLS,
    )

    return str(model.predict(X)[0])


# ── Standalone retrain ────────────────────────────────────────────────────────

if __name__ == "__main__":
    train_and_save()