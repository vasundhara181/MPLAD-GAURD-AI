import pandas as pd
from preprocessing import preprocess_projects


def detect_delays():

    # Load preprocessed data
    df = preprocess_projects()

    # Create delay flag
    df["delay_anomaly"] = False

    # Create delay risk score
    df["delay_risk_score"] = 0.0

    # -------------------------------------------------
    # RULE 1
    # Project is already beyond expected completion
    # -------------------------------------------------

    condition_1 = (
        df["delay_days"] > 0
    )

    df.loc[condition_1, "delay_anomaly"] = True
    df.loc[condition_1, "delay_risk_score"] += 40

    # -------------------------------------------------
    # RULE 2
    # Delay greater than 30 days
    # -------------------------------------------------

    condition_2 = (
        df["delay_days"] > 30
    )

    df.loc[condition_2, "delay_risk_score"] += 20

    # -------------------------------------------------
    # RULE 3
    # Delay greater than 90 days
    # -------------------------------------------------

    condition_3 = (
        df["delay_days"] > 90
    )

    df.loc[condition_3, "delay_risk_score"] += 20

    # -------------------------------------------------
    # RULE 4
    # Project is overdue but not completed
    # -------------------------------------------------

    condition_4 = (
        (df["delay_days"] > 0)
        & (df["status"].str.lower() != "completed")
    )

    df.loc[condition_4, "delay_anomaly"] = True
    df.loc[condition_4, "delay_risk_score"] += 20

    # -------------------------------------------------
    # RULE 5
    # Project has been running for a very long time
    # -------------------------------------------------

    condition_5 = (
        df["actual_duration_days"]
        > df["planned_duration_days"] * 1.5
    )

    df.loc[condition_5, "delay_anomaly"] = True
    df.loc[condition_5, "delay_risk_score"] += 20

    # -------------------------------------------------
    # Limit score to 0–100
    # -------------------------------------------------

    df["delay_risk_score"] = (
        df["delay_risk_score"].clip(upper=100)
    )

    return df


if __name__ == "__main__":

    df = detect_delays()

    delayed_projects = df[
        df["delay_anomaly"] == True
    ].copy()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("    DELAY & STALLED PROJECT DETECTION")
    print("==========================================")

    print("\nTotal projects:", len(df))

    print(
        "Delayed/stalled projects detected:",
        len(delayed_projects)
    )

    print("\nTop delay-risk projects:\n")

    columns = [
        "project_id",
        "project_name",
        "status",
        "completion_percentage",
        "planned_duration_days",
        "actual_duration_days",
        "delay_days",
        "delay_risk_score"
    ]

    print(
        delayed_projects[
            columns
        ]
        .sort_values(
            "delay_risk_score",
            ascending=False
        )
        .head(20)
        .to_string(index=False)
    )