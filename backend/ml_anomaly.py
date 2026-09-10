"""
Unsupervised ML anomaly detection.

The other risk modules are hand-written threshold rules. This module is
genuinely model-based: it fits an Isolation Forest on a handful of
numeric project features and scores every project by how much of an
outlier it is relative to the rest of the portfolio -- catching
combinations of values a fixed threshold would never anticipate.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from preprocessing import preprocess_projects

FEATURE_COLUMNS = [
    "utilization_percentage",
    "completion_percentage",
    "progress_mismatch_abs",
    "delay_days",
]

MIN_ROWS_TO_FIT = 20


def detect_ml_anomalies() -> pd.DataFrame:
    df = preprocess_projects().copy()

    available_features = [
        col for col in FEATURE_COLUMNS
        if col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().sum() >= MIN_ROWS_TO_FIT
    ]

    result = df[["project_id"]].copy()

    if len(available_features) < 2 or len(df) < MIN_ROWS_TO_FIT:
        result["ml_anomaly"] = False
        result["ml_anomaly_score"] = 0.0
        result["ml_top_feature"] = ""
        result["ml_signal_available"] = False
        return result

    features = df[available_features].apply(pd.to_numeric, errors="coerce")
    medians = features.median()
    features = features.fillna(medians)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
    )

    model.fit(features)

    # score_samples: higher = more normal, lower (more negative) = more anomalous.
    raw_scores = model.score_samples(features)
    predictions = model.predict(features)

    low, high = raw_scores.min(), raw_scores.max()

    if high - low < 1e-9:
        normalized = np.zeros(len(raw_scores))
    else:
        normalized = (high - raw_scores) / (high - low)

    result["ml_anomaly"] = predictions == -1
    result["ml_anomaly_score"] = np.round(normalized * 100, 2)

    # Lightweight explanation: which feature deviates furthest (in z-score
    # terms) from the portfolio average for this project.
    stds = features.std().replace(0, 1)
    z_scores = ((features - medians) / stds).abs()
    result["ml_top_feature"] = z_scores.idxmax(axis=1)
    result["ml_top_feature_z"] = z_scores.max(axis=1).round(2)
    result["ml_signal_available"] = True

    return result


if __name__ == "__main__":
    df = detect_ml_anomalies()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("     ML ANOMALY DETECTION (Isolation Forest)")
    print("==========================================")

    print("\nTotal projects:", len(df))
    print("Flagged as ML anomalies:", int(df["ml_anomaly"].sum()))

    if df["ml_signal_available"].iloc[0]:
        print(
            "\nTop 15 by ML anomaly score:\n",
            df.sort_values("ml_anomaly_score", ascending=False)
            .head(15)
            .to_string(index=False),
        )
    else:
        print("\nNot enough numeric data to fit a model on this dataset.")
