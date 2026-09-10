import threading

import pandas as pd

from citizen_feedback import citizen_feedback_fingerprint
from data_loader import dataset_fingerprint
from explainability import build_explainable_risk

_cache = {"key": None, "df": None}
_cache_lock = threading.Lock()


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

    if any("ml model" in reason.lower() or "isolation forest" in reason.lower() for reason in reasons):
        return "ML ANOMALY ALERT"

    if any("duplicate" in reason.lower() or "re-registered" in reason.lower() for reason in reasons):
        return "DUPLICATE PROJECT ALERT"

    if any("location overlaps" in reason.lower() for reason in reasons):
        return "GEO-SPATIAL OVERLAP ALERT"

    if any("citizen report" in reason.lower() for reason in reasons):
        return "CITIZEN REPORTED ALERT"

    return "GENERAL REVIEW ALERT"


def build_smart_alerts():
    """Cached wrapper: the full 9-signal pipeline (rule-based modules +
    Isolation Forest + TF-IDF duplicate detection) is expensive, and
    every dashboard load hits several endpoints that each need this
    same result (summary, analysis, insights, alerts). Recompute only
    when the active dataset actually changes (upload/reset), not on
    every request."""

    key = dataset_fingerprint() + "|" + citizen_feedback_fingerprint()

    if _cache["key"] == key and _cache["df"] is not None:
        return _cache["df"].copy()

    # Serialize computation: without this, several requests racing on a
    # cold cache (e.g. a dashboard's first load, which hits 4+ endpoints
    # in parallel) would each independently run the full pipeline.
    with _cache_lock:
        if _cache["key"] == key and _cache["df"] is not None:
            return _cache["df"].copy()

        df = _compute_smart_alerts()

        _cache["key"] = key
        _cache["df"] = df

    return df.copy()


def _compute_smart_alerts():

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
    #
    # A weighted blend is right for *ranking* projects, but it can
    # bury one sharp, specific finding (e.g. 100% of funds released
    # instantly, or a near-duplicate project elsewhere) under a wash
    # of quiet signals, since each individual signal only carries a
    # fraction of the total weight. So a project also qualifies for
    # an alert if any single high-precision, low-noise signal fires
    # on its own -- these are the ones with a clear rule/model behind
    # them (not just "somewhat overdue," which is common enough in a
    # real portfolio that it belongs in the blended score, not an
    # independent trigger).
    # ------------------------------------------------

    sharp_signal_columns = [
        "financial_anomaly",
        "document_anomaly",
        "image_anomaly",
        "duplicate_anomaly",
        "geo_anomaly",
        "ml_anomaly",
        "citizen_anomaly",
    ]

    df["sharp_signal_fired"] = df[sharp_signal_columns].any(axis=1)

    df["alert_required"] = (
        (df["overall_risk_score"] >= 40)
        | df["sharp_signal_fired"]
    )

    # ------------------------------------------------
    # ALERT SEVERITY
    # ------------------------------------------------

    df["alert_severity"] = "NONE"

    df.loc[
        df["sharp_signal_fired"],
        "alert_severity"
    ] = "MEDIUM"

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