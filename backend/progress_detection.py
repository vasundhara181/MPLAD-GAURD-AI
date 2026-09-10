import pandas as pd
from preprocessing import preprocess_projects


def detect_progress_mismatch():

    # Load preprocessed project data
    df = preprocess_projects()

    # Create anomaly flag
    df["progress_anomaly"] = False

    # Create risk score
    df["progress_risk_score"] = 0.0

    # -------------------------------------------------
    # RULE 1
    # Financial progress is more than 20% ahead
    # of physical completion
    # -------------------------------------------------

    condition_1 = (
        df["progress_mismatch"] > 20
    )

    df.loc[condition_1, "progress_anomaly"] = True
    df.loc[condition_1, "progress_risk_score"] += 40

    # -------------------------------------------------
    # RULE 2
    # Financial progress is more than 40% ahead
    # -------------------------------------------------

    condition_2 = (
        df["progress_mismatch"] > 40
    )

    df.loc[condition_2, "progress_risk_score"] += 25

    # -------------------------------------------------
    # RULE 3
    # Very large mismatch in either direction
    # -------------------------------------------------

    condition_3 = (
        df["progress_mismatch_abs"] > 50
    )

    df.loc[condition_3, "progress_anomaly"] = True
    df.loc[condition_3, "progress_risk_score"] += 20

    # -------------------------------------------------
    # RULE 4
    # High financial utilization but low physical work
    # -------------------------------------------------

    condition_4 = (
        (df["utilization_percentage"] > 80)
        & (df["completion_percentage"] < 50)
    )

    df.loc[condition_4, "progress_anomaly"] = True
    df.loc[condition_4, "progress_risk_score"] += 30

    # -------------------------------------------------
    # Limit score to 100
    # -------------------------------------------------

    df["progress_risk_score"] = (
        df["progress_risk_score"].clip(upper=100)
    )

    return df


if __name__ == "__main__":

    df = detect_progress_mismatch()

    anomalies = df[
        df["progress_anomaly"] == True
    ].copy()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("     PROGRESS MISMATCH DETECTION")
    print("==========================================")

    print("\nTotal projects:", len(df))

    print(
        "Progress mismatch projects detected:",
        len(anomalies)
    )

    print("\nTop progress-risk projects:\n")

    columns = [
        "project_id",
        "project_name",
        "completion_percentage",
        "financial_progress_percentage",
        "utilization_percentage",
        "progress_mismatch",
        "progress_risk_score"
    ]

    print(
        anomalies[
            columns
        ]
        .sort_values(
            "progress_risk_score",
            ascending=False
        )
        .head(20)
        .to_string(index=False)
    )