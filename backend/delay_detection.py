import pandas as pd
from preprocessing import preprocess_projects


def detect_delays():

    # Load preprocessed data
    df = preprocess_projects()

    # Create delay flag
    df["delay_anomaly"] = False

    # Create delay risk score
    df["delay_risk_score"] = 0.0

    status_lower = df["status"].fillna("").astype(str).str.lower()

    # -------------------------------------------------
    # RULE 1 (primary trigger)
    # The project's own recorded status says "Delayed".
    #
    # A today-vs-expected-completion-date comparison silently
    # drifts as real time passes relative to when a dataset
    # snapshot was captured -- a project sanctioned to finish in
    # 2025 looks "delayed by a year" if this runs in 2026, whether
    # or not it's actually behind schedule as of its own last
    # known status. The status field doesn't have that problem,
    # and it's a standard field in real project-tracking data.
    # -------------------------------------------------

    condition_1 = status_lower == "delayed"

    df.loc[condition_1, "delay_anomaly"] = True
    df.loc[condition_1, "delay_risk_score"] += 60

    # -------------------------------------------------
    # RULES 2-4 (severity escalation only)
    #
    # These only ADD to the score of a project already flagged by
    # Rule 1 -- they deliberately do not set delay_anomaly on their
    # own. A fixed day-count threshold can't distinguish "genuinely
    # overdue" from "this dataset is simply older than today" without
    # knowing how current the dataset actually is, so using it as an
    # independent trigger produces exactly that false-positive rate
    # on a dataset whose reference date has drifted.
    # -------------------------------------------------

    already_flagged = df["delay_anomaly"]

    df.loc[already_flagged & (df["delay_days"] > 90), "delay_risk_score"] += 15
    df.loc[already_flagged & (df["delay_days"] > 180), "delay_risk_score"] += 15

    df.loc[
        already_flagged
        & (df["actual_duration_days"] > df["planned_duration_days"] * 1.5),
        "delay_risk_score"
    ] += 10

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
