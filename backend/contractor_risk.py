import pandas as pd
from preprocessing import preprocess_projects


def calculate_contractor_risk():

    df = preprocess_projects().copy()

    # Make sure contractor names are usable
    df["contractor"] = (
        df["contractor"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    # -------------------------------------------------
    # Aggregate contractor performance
    # -------------------------------------------------

    contractor_summary = (
        df.groupby("contractor")
        .agg(
            total_projects=("project_id", "count"),

            average_completion=(
                "completion_percentage",
                "mean"
            ),

            average_delay_days=(
                "delay_days",
                "mean"
            ),

            total_utilized_amount=(
                "utilized_amount",
                "sum"
            ),

            financial_anomalies=(
                "project_id",
                "count"
            )
        )
        .reset_index()
    )

    # -------------------------------------------------
    # Count actual anomaly types separately
    # -------------------------------------------------

    financial_counts = (
        df.groupby("contractor")["project_id"]
        .count()
        .rename("project_count")
    )

    # Uses the project's own recorded status, not a today-vs-expected
    # -completion-date comparison -- delay_days drifts with wall-clock
    # time relative to when the dataset was captured (see
    # delay_detection.py), which would otherwise make this aggregate
    # inflate for nearly every contractor as a dataset ages.
    is_delayed_status = (
        df["status"].fillna("").astype(str).str.lower() == "delayed"
    )

    delay_counts = (
        df[is_delayed_status]
        .groupby("contractor")["project_id"]
        .count()
        .rename("delayed_projects")
    )

    progress_counts = (
        df[df["progress_mismatch_abs"] > 30]
        .groupby("contractor")["project_id"]
        .count()
        .rename("progress_mismatch_projects")
    )

    contractor_summary = contractor_summary.drop(
        columns=["financial_anomalies"]
    )

    contractor_summary = contractor_summary.merge(
        financial_counts,
        on="contractor",
        how="left"
    )

    contractor_summary = contractor_summary.merge(
        delay_counts,
        on="contractor",
        how="left"
    )

    contractor_summary = contractor_summary.merge(
        progress_counts,
        on="contractor",
        how="left"
    )

    contractor_summary[
        [
            "delayed_projects",
            "progress_mismatch_projects"
        ]
    ] = contractor_summary[
        [
            "delayed_projects",
            "progress_mismatch_projects"
        ]
    ].fillna(0)

    # -------------------------------------------------
    # Contractor risk score
    # -------------------------------------------------

    contractor_summary["contractor_risk_score"] = 0.0

    # More delayed projects → higher risk
    contractor_summary.loc[
        contractor_summary["delayed_projects"] >= 2,
        "contractor_risk_score"
    ] += 30

    contractor_summary.loc[
        contractor_summary["delayed_projects"] >= 5,
        "contractor_risk_score"
    ] += 20

    # More progress mismatches → higher risk
    contractor_summary.loc[
        contractor_summary["progress_mismatch_projects"] >= 2,
        "contractor_risk_score"
    ] += 25

    contractor_summary.loc[
        contractor_summary["progress_mismatch_projects"] >= 5,
        "contractor_risk_score"
    ] += 15

    # Very low average completion
    contractor_summary.loc[
        contractor_summary["average_completion"] < 50,
        "contractor_risk_score"
    ] += 20

    # Limit score to 100
    contractor_summary["contractor_risk_score"] = (
        contractor_summary["contractor_risk_score"]
        .clip(upper=100)
    )

    # -------------------------------------------------
    # Risk category
    # -------------------------------------------------

    def risk_category(score):

        if score >= 70:
            return "HIGH"

        elif score >= 40:
            return "MEDIUM"

        return "LOW"

    contractor_summary["risk_level"] = (
        contractor_summary["contractor_risk_score"]
        .apply(risk_category)
    )

    return contractor_summary


if __name__ == "__main__":

    result = calculate_contractor_risk()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("        CONTRACTOR RISK ANALYSIS")
    print("==========================================")

    print(
        "\nTotal contractors:",
        len(result)
    )

    print("\nContractor risk summary:\n")

    columns = [
        "contractor",
        "total_projects",
        "delayed_projects",
        "progress_mismatch_projects",
        "average_completion",
        "average_delay_days",
        "contractor_risk_score",
        "risk_level"
    ]

    print(
        result
        .sort_values(
            "contractor_risk_score",
            ascending=False
        )
        [columns]
        .head(20)
        .to_string(index=False)
    )