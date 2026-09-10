import pandas as pd
from preprocessing import preprocess_projects


def detect_financial_anomalies():

    # Load preprocessed project data
    df = preprocess_projects()

    # Create financial anomaly flag
    df["financial_anomaly"] = False

    # Create financial risk score
    df["financial_risk_score"] = 0.0

    # -------------------------------------------------
    # RULE 1
    # Utilized amount > sanctioned amount
    # -------------------------------------------------

    condition_1 = (
        df["utilized_amount"] > df["sanctioned_amount"]
    )

    df.loc[condition_1, "financial_anomaly"] = True
    df.loc[condition_1, "financial_risk_score"] += 40

    # -------------------------------------------------
    # RULE 2
    # Released amount > sanctioned amount
    # -------------------------------------------------

    condition_2 = (
        df["released_amount"] > df["sanctioned_amount"]
    )

    df.loc[condition_2, "financial_anomaly"] = True
    df.loc[condition_2, "financial_risk_score"] += 30

    # -------------------------------------------------
    # RULE 3
    # Very high utilization
    # -------------------------------------------------

    condition_3 = (
        df["utilization_percentage"] > 95
    )

    df.loc[condition_3, "financial_risk_score"] += 15

    # -------------------------------------------------
    # RULE 4
    # Large financial-progress mismatch
    # -------------------------------------------------

    condition_4 = (
        df["progress_mismatch_abs"] > 30
    )

    df.loc[condition_4, "financial_anomaly"] = True
    df.loc[condition_4, "financial_risk_score"] += 25

    # -------------------------------------------------
    # RULE 5
    # No utilization but project has started
    # -------------------------------------------------

    condition_5 = (
        (df["utilized_amount"] <= 0)
        & (df["completion_percentage"] > 0)
    )

    df.loc[condition_5, "financial_anomaly"] = True
    df.loc[condition_5, "financial_risk_score"] += 20

    # -------------------------------------------------
    # Limit financial score to 0–100
    # -------------------------------------------------

    df["financial_risk_score"] = (
        df["financial_risk_score"].clip(upper=100)
    )

    return df


if __name__ == "__main__":

    df = detect_financial_anomalies()

    anomalies = df[
        df["financial_anomaly"] == True
    ].copy()

    print("\n==========================================")
    print("       MPLAD-GUARD AI")
    print("   FINANCIAL ANOMALY DETECTION")
    print("==========================================")

    print("\nTotal projects:", len(df))

    print(
        "Financial anomalies detected:",
        len(anomalies)
    )

    print("\nTop financial-risk projects:\n")

    columns = [
        "project_id",
        "project_name",
        "sanctioned_amount",
        "released_amount",
        "utilized_amount",
        "utilization_percentage",
        "progress_mismatch",
        "financial_risk_score"
    ]

    print(
        anomalies[
            columns
        ]
        .sort_values(
            "financial_risk_score",
            ascending=False
        )
        .head(20)
        .to_string(index=False)
    )