"""
Portfolio-level AI insights.

Everything here is a pure aggregation over the already-computed risk
scores from smart_alerts.build_smart_alerts() -- it requires zero human
input. This is the "complete overview analysis" layer: instead of only
a per-project score, it answers portfolio-wide questions (which
districts/contractors/project types concentrate risk, how much
sanctioned money sits in HIGH/CRITICAL projects, which of the 9 AI
signals fires most often) automatically, for every project, every time
the dataset changes.
"""

import pandas as pd

from geo_detection import detect_geo_anomalies
from smart_alerts import build_smart_alerts

ANOMALY_COLUMNS = [
    "financial_anomaly",
    "delay_anomaly",
    "progress_anomaly",
    "document_anomaly",
    "image_anomaly",
    "inspection_anomaly",
    "ml_anomaly",
    "duplicate_anomaly",
    "geo_anomaly",
    "citizen_anomaly",
]

SIGNAL_LABELS = {
    "financial_anomaly": "Financial",
    "delay_anomaly": "Delay",
    "progress_anomaly": "Progress",
    "document_anomaly": "Document",
    "image_anomaly": "Image",
    "inspection_anomaly": "Inspection",
    "ml_anomaly": "ML Anomaly",
    "duplicate_anomaly": "Duplicate",
    "geo_anomaly": "Geo-Spatial Overlap",
    "citizen_anomaly": "Citizen Reported",
}

MIN_GROUP_SIZE = 2


def _group_risk_ranking(df: pd.DataFrame, group_column: str, top_n: int = 10):
    if group_column not in df.columns:
        return []

    working = df.copy()
    working[group_column] = working[group_column].fillna("Unknown").astype(str).str.strip()
    working = working[working[group_column] != ""]

    # Uses the same alert_required flag as the Live Alerts feed and the
    # "Active Alerts" stat card (overall score >= 40 OR a sharp,
    # low-noise signal fired on its own) so "flagged" means the same
    # thing on every panel of the dashboard.
    is_flagged = working["alert_required"]

    grouped = (
        working.groupby(group_column)
        .agg(
            project_count=("project_id", "count"),
            average_risk_score=("overall_risk_score", "mean"),
            flagged_count=(
                "alert_required",
                lambda s: int(s.sum()),
            ),
            sanctioned_amount_at_risk=(
                "sanctioned_amount",
                lambda s: float(s[is_flagged.loc[s.index]].sum()),
            ),
        )
        .reset_index()
        .rename(columns={group_column: "name"})
    )

    grouped = grouped[grouped["project_count"] >= MIN_GROUP_SIZE]

    grouped["average_risk_score"] = grouped["average_risk_score"].round(2)

    grouped = grouped.sort_values(
        "average_risk_score", ascending=False
    ).head(top_n)

    return grouped.to_dict(orient="records")


def build_portfolio_insights() -> dict:
    df = build_smart_alerts()

    total_projects = len(df)

    flagged = df[df["alert_required"]]

    total_sanctioned = float(pd.to_numeric(df["sanctioned_amount"], errors="coerce").fillna(0).sum())

    sanctioned_at_risk = float(
        pd.to_numeric(flagged["sanctioned_amount"], errors="coerce").fillna(0).sum()
    )

    signal_frequency = []

    for column in ANOMALY_COLUMNS:
        if column not in df.columns:
            continue

        count = int(df[column].fillna(False).astype(bool).sum())

        signal_frequency.append({
            "signal": SIGNAL_LABELS.get(column, column),
            "flagged_projects": count,
            "percentage": round((count / total_projects) * 100, 1) if total_projects else 0,
        })

    signal_frequency.sort(key=lambda row: row["flagged_projects"], reverse=True)

    # ------------------------------------------------
    # Project status breakdown -- completed / in progress / delayed /
    # not started / other, straight from each project's own recorded
    # status field.
    # ------------------------------------------------

    status_breakdown = []

    if "status" in df.columns and total_projects:
        status_clean = df["status"].fillna("Unknown").astype(str).str.strip()
        status_clean = status_clean.where(status_clean != "", "Unknown")

        for label, count in status_clean.value_counts().items():
            status_breakdown.append({
                "status": label,
                "count": int(count),
                "percentage": round((int(count) / total_projects) * 100, 1),
            })

    # ------------------------------------------------
    # Real-time fund tracking -- aggregate fund flow across the
    # whole portfolio, recomputed on every request from whatever
    # dataset is currently loaded.
    # ------------------------------------------------

    total_released = float(pd.to_numeric(df["released_amount"], errors="coerce").fillna(0).sum())
    total_utilized = float(pd.to_numeric(df["utilized_amount"], errors="coerce").fillna(0).sum())
    unutilized_funds = round(total_released - total_utilized, 2)

    fund_tracking = {
        "total_sanctioned": round(total_sanctioned, 2),
        "total_released": round(total_released, 2),
        "total_utilized": round(total_utilized, 2),
        "unutilized_funds": unutilized_funds,
        "utilization_rate_percentage": (
            round((total_utilized / total_released) * 100, 1) if total_released else 0
        ),
        "release_rate_percentage": (
            round((total_released / total_sanctioned) * 100, 1) if total_sanctioned else 0
        ),
    }

    # ------------------------------------------------
    # Geo-spatial overlap pairs -- exact project pairs whose
    # sanctioned locations sit suspiciously close together.
    # ------------------------------------------------

    geo_pairs_df = detect_geo_anomalies()

    geo_overlap_pairs = (
        geo_pairs_df.sort_values("distance_km").head(20).to_dict(orient="records")
        if not geo_pairs_df.empty else []
    )

    return {
        "total_projects": total_projects,
        "flagged_projects": int(len(flagged)),
        "flagged_percentage": (
            round((len(flagged) / total_projects) * 100, 1)
            if total_projects else 0
        ),
        "total_sanctioned_amount": round(total_sanctioned, 2),
        "sanctioned_amount_at_risk": round(sanctioned_at_risk, 2),
        "sanctioned_at_risk_percentage": (
            round((sanctioned_at_risk / total_sanctioned) * 100, 1)
            if total_sanctioned else 0
        ),
        "fund_tracking": fund_tracking,
        "geo_overlap_pairs": geo_overlap_pairs,
        "status_breakdown": status_breakdown,
        "signal_frequency": signal_frequency,
        "risk_by_state": _group_risk_ranking(df, "state"),
        "risk_by_district": _group_risk_ranking(df, "district"),
        "risk_by_project_type": _group_risk_ranking(df, "project_type"),
        "risk_by_contractor": _group_risk_ranking(df, "contractor"),
    }


if __name__ == "__main__":
    insights = build_portfolio_insights()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("       PORTFOLIO INSIGHTS (fully automatic)")
    print("==========================================")

    print(f"\nTotal projects: {insights['total_projects']}")
    print(
        f"Flagged (alert_required): {insights['flagged_projects']} "
        f"({insights['flagged_percentage']}%)"
    )
    print(
        f"Sanctioned amount at risk: Rs.{insights['sanctioned_amount_at_risk']:,.0f} "
        f"of Rs.{insights['total_sanctioned_amount']:,.0f} "
        f"({insights['sanctioned_at_risk_percentage']}%)"
    )

    print("\nSignal frequency across portfolio:")
    for row in insights["signal_frequency"]:
        print(f"  {row['signal']:<12} {row['flagged_projects']:>4} projects ({row['percentage']}%)")

    print("\nTop districts by average risk score:")
    for row in insights["risk_by_district"][:5]:
        print(f"  {row['name']:<20} avg={row['average_risk_score']:>6}  n={row['project_count']}")
