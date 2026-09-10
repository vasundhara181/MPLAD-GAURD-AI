import pandas as pd

from risk_fusion import build_risk_fusion


def generate_explanation(row):

    reasons = []

    # ---------------------------------------------
    # FINANCIAL
    # ---------------------------------------------

    if row["financial_anomaly"]:

        score = row["financial_risk_score"]

        if score >= 70:
            reasons.append(
                f"Significant financial anomaly detected "
                f"(financial risk: {score:.0f}/100)"
            )

        else:
            reasons.append(
                f"Financial irregularity detected "
                f"(financial risk: {score:.0f}/100)"
            )

    # ---------------------------------------------
    # DELAY
    # ---------------------------------------------

    if row["delay_anomaly"]:

        delay_days = row.get("delay_days", 0)

        if pd.notna(delay_days) and delay_days > 0:

            reasons.append(
                f"Project is delayed by approximately "
                f"{int(delay_days)} days"
            )

        else:

            reasons.append(
                "Project shows a delay/stalling signal"
            )

    # ---------------------------------------------
    # PROGRESS
    # ---------------------------------------------

    if row["progress_anomaly"]:

        mismatch = row.get(
            "progress_mismatch",
            0
        )

        if pd.notna(mismatch):

            reasons.append(
                f"Financial and physical progress "
                f"show a mismatch of approximately "
                f"{abs(float(mismatch)):.1f}%"
            )

        else:

            reasons.append(
                "Financial and physical progress mismatch detected"
            )

    # ---------------------------------------------
    # DOCUMENT
    # ---------------------------------------------

    if row["document_anomaly"]:

        if row.get("amount_mismatch", False):

            reasons.append(
                "Document amount does not match "
                "the project expenditure"
            )

        if row.get("contractor_mismatch", False):

            reasons.append(
                "Contractor information differs "
                "between project and document records"
            )

        if row.get("location_mismatch", False):

            reasons.append(
                "Project location differs from "
                "the document location"
            )

        if row.get("missing_document", False):

            reasons.append(
                "Required project document is missing"
            )

    # ---------------------------------------------
    # IMAGE
    # ---------------------------------------------

    if row["image_anomaly"]:

        if row.get("reused_image", False):

            reasons.append(
                "Potentially reused project image detected"
            )

        elif row.get("high_similarity", False):

            similarity = row.get(
                "similarity_score",
                0
            )

            reasons.append(
                f"Highly similar image detected "
                f"(similarity: {float(similarity):.2f})"
            )

        elif row.get("missing_image", False):

            reasons.append(
                "Project does not have image evidence"
            )

        else:

            reasons.append(
                "Image evidence requires verification"
            )

    # ---------------------------------------------
    # INSPECTION
    # ---------------------------------------------

    if row["inspection_anomaly"]:

        if row.get("failed_inspection", False):

            reasons.append(
                "Latest inspection was marked as FAILED"
            )

        elif row.get("needs_improvement", False):

            reasons.append(
                "Inspection indicates that "
                "improvement is required"
            )

        elif row.get("low_inspection_score", False):

            score = row.get(
                "inspection_score",
                0
            )

            reasons.append(
                f"Low inspection score detected "
                f"({float(score):.0f}/100)"
            )

        elif row.get("missing_inspection", False):

            reasons.append(
                "Inspection evidence is missing"
            )

    # ---------------------------------------------
    # ML ANOMALY (Isolation Forest)
    # ---------------------------------------------

    if row.get("ml_anomaly"):

        top_feature = row.get("ml_top_feature", "")
        score = row.get("ml_anomaly_score", 0)

        feature_labels = {
            "utilization_percentage": "fund utilization",
            "completion_percentage": "physical completion",
            "progress_mismatch_abs": "financial-vs-physical progress mismatch",
            "delay_days": "schedule delay",
        }

        label = feature_labels.get(top_feature, top_feature or "its overall profile")

        reasons.append(
            f"ML model (Isolation Forest) flags this project as a "
            f"statistical outlier versus similar projects, driven "
            f"mostly by {label} (anomaly score: {float(score):.0f}/100)"
        )

    # ---------------------------------------------
    # DUPLICATE / RE-REGISTERED PROJECT
    # ---------------------------------------------

    if row.get("duplicate_anomaly"):

        reasons.append(
            "Project name/type/location closely matches another "
            "project in the portfolio (possible duplicate or "
            "re-registered work)"
        )

    # ---------------------------------------------
    # CONTRACTOR
    # ---------------------------------------------

    contractor_score = row.get(
        "contractor_risk_score",
        0
    )

    if pd.notna(contractor_score):

        if contractor_score >= 70:

            reasons.append(
                f"Contractor shows elevated historical "
                f"risk pattern ({contractor_score:.0f}/100)"
            )

        elif contractor_score >= 40:

            reasons.append(
                f"Contractor shows moderate historical "
                f"risk pattern ({contractor_score:.0f}/100)"
            )

    # ---------------------------------------------
    # DEFAULT
    # ---------------------------------------------

    if not reasons:

        reasons.append(
            "No significant anomaly signals detected"
        )

    return reasons


def add_explanations(df):

    explanations = []

    for _, row in df.iterrows():

        reasons = generate_explanation(row)

        explanations.append(
            reasons
        )

    df = df.copy()

    df["risk_reasons"] = explanations

    df["risk_reason_count"] = (
        df["risk_reasons"]
        .apply(len)
    )

    return df


def build_explainable_risk():

    df = build_risk_fusion()

    df = add_explanations(df)

    return df


if __name__ == "__main__":

    df = build_explainable_risk()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("       EXPLAINABLE RISK ENGINE")
    print("==========================================")

    print(
        "\nProjects analyzed:",
        len(df)
    )

    print(
        "Projects with risk signals:",
        int(
            (df["risk_signal_count"] > 0)
            .sum()
        )
    )

    # Top risky projects
    top_projects = (
        df.sort_values(
            "overall_risk_score",
            ascending=False
        )
        .head(10)
    )

    for _, row in top_projects.iterrows():

        print("\n------------------------------------------")

        print(
            "Project:",
            row["project_id"]
        )

        print(
            "Name:",
            row["project_name"]
        )

        print(
            "Risk Score:",
            row["overall_risk_score"]
        )

        print(
            "Risk Level:",
            row["risk_level"]
        )

        print(
            "Risk Signals:",
            row["risk_signal_count"]
        )

        print("\nWhy was this project flagged?")

        for reason in row["risk_reasons"]:

            print(
                "  -",
                reason
            )