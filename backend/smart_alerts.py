import pandas as pd

from explainability import build_explainable_risk


def determine_priority(row):

    score = row["overall_risk_score"]
    signals = row["risk_signal_count"]

    if score >= 90:
        return "P1 - IMMEDIATE"

    elif score >= 70:
        return "P2 - HIGH PRIORITY"

    elif score >= 40:
        return "P3 - MONITOR"

    elif signals > 0:
        return "P4 - REVIEW"

    else:
        return "P5 - NORMAL"


def determine_action(row):

    score = row["overall_risk_score"]

    if score >= 90:
        return "Immediate human verification / field inspection"

    elif score >= 70:
        return "Priority investigation by responsible authority"

    elif score >= 40:
        return "Monitor project and review supporting evidence"

    elif row["risk_signal_count"] > 0:
        return "Routine verification recommended"

    else:
        return "No immediate action required"


def determine_alert_type(row):

    reasons = row["risk_reasons"]

    if row["risk_level"] == "CRITICAL":
        return "CRITICAL RISK ALERT"

    if row["risk_level"] == "HIGH":
        return "HIGH RISK ALERT"

    if any("financial" in reason.lower() for reason in reasons):
        return "FINANCIAL ALERT"

    if any("delay" in reason.lower() for reason in reasons):
        return "DELAY ALERT"

    if any("document" in reason.lower() for reason in reasons):
        return "DOCUMENT ALERT"

    if any("inspection" in reason.lower() for reason in reasons):
        return "INSPECTION ALERT"

    if any("image" in reason.lower() for reason in reasons):
        return "IMAGE EVIDENCE ALERT"

    return "GENERAL REVIEW ALERT"


def build_smart_alerts():

    df = build_explainable_risk().copy()

    # ------------------------------------------------
    # PRIORITY
    # ------------------------------------------------

    df["priority"] = df.apply(
        determine_priority,
        axis=1
    )

    # ------------------------------------------------
    # RECOMMENDED ACTION
    # ------------------------------------------------

    df["recommended_action"] = df.apply(
        determine_action,
        axis=1
    )

    # ------------------------------------------------
    # ALERT TYPE
    # ------------------------------------------------

    df["alert_type"] = df.apply(
        determine_alert_type,
        axis=1
    )

    # ------------------------------------------------
    # ALERT FLAG
    # ------------------------------------------------

    df["alert_required"] = (
        df["overall_risk_score"] >= 40
    )

    # ------------------------------------------------
    # ALERT SEVERITY
    # ------------------------------------------------

    df["alert_severity"] = "NONE"

    df.loc[
        df["overall_risk_score"] >= 40,
        "alert_severity"
    ] = "MEDIUM"

    df.loc[
        df["overall_risk_score"] >= 70,
        "alert_severity"
    ] = "HIGH"

    df.loc[
        df["overall_risk_score"] >= 90,
        "alert_severity"
    ] = "CRITICAL"

    # ------------------------------------------------
    # SORT FOR INVESTIGATION
    # ------------------------------------------------

    df = df.sort_values(
        [
            "overall_risk_score",
            "risk_signal_count"
        ],
        ascending=False
    ).reset_index(drop=True)

    # Investigation rank
    df["investigation_rank"] = (
        df.index + 1
    )

    return df


if __name__ == "__main__":

    df = build_smart_alerts()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("       SMART ALERT ENGINE")
    print("==========================================")

    print(
        "\nTotal projects:",
        len(df)
    )

    print(
        "Alerts generated:",
        int(df["alert_required"].sum())
    )

    print("\nAlert severity distribution:\n")

    print(
        df["alert_severity"]
        .value_counts()
        .to_string()
    )

    print("\nPriority distribution:\n")

    print(
        df["priority"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nTop priority projects:\n")

    columns = [
        "investigation_rank",
        "project_id",
        "project_name",
        "overall_risk_score",
        "risk_level",
        "alert_severity",
        "priority",
        "risk_signal_count",
        "recommended_action"
    ]

    print(
        df[columns]
        .head(20)
        .to_string(index=False)
    )

    print("\n==========================================")
    print("       CRITICAL / HIGH ALERTS")
    print("==========================================")

    critical_high = df[
        df["risk_level"].isin(
            ["CRITICAL", "HIGH"]
        )
    ]

    if len(critical_high) == 0:

        print("\nNo Critical or High-risk projects.")

    else:

        for _, row in critical_high.head(10).iterrows():

            print("\n------------------------------------------")

            print(
                "Project:",
                row["project_id"]
            )

            print(
                "Risk:",
                row["overall_risk_score"],
                "/ 100"
            )

            print(
                "Level:",
                row["risk_level"]
            )

            print(
                "Priority:",
                row["priority"]
            )

            print(
                "Alert:",
                row["alert_type"]
            )

            print(
                "Action:",
                row["recommended_action"]
            )

            print("Reasons:")

            for reason in row["risk_reasons"]:

                print(" -", reason)