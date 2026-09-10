import pandas as pd

from data_loader import get_data_availability
from financial_anomaly import detect_financial_anomalies
from delay_detection import detect_delays
from progress_detection import detect_progress_mismatch
from contractor_risk import calculate_contractor_risk
from document_verification import verify_documents
from image_verification import verify_images
from inspection_analysis import analyze_inspections
from ml_anomaly import detect_ml_anomalies
from duplicate_detection import build_duplicate_risk

# ==================================================================
# SIGNAL WEIGHTS
#
# These sum to 1.0 across a "complete" dataset (every signal
# available). When a dataset is missing the inputs a signal needs
# (e.g. no documents.csv was supplied, or the projects file has no
# date columns to compute delay from), that signal is excluded and
# the remaining weights are rescaled to still sum to 1.0 -- so a
# partial dataset produces a fair score instead of one silently
# deflated by signals that never had a chance to run.
# ==================================================================

SIGNAL_WEIGHTS = {
    "financial": 0.15,
    "delay": 0.15,
    "progress": 0.15,
    "contractor": 0.10,
    "document": 0.10,
    "image": 0.10,
    "inspection": 0.15,
    "ml_anomaly": 0.05,
    "duplicate": 0.05,
}


def calculate_risk_level(score):

    if score >= 90:
        return "CRITICAL"

    elif score >= 70:
        return "HIGH"

    elif score >= 40:
        return "MEDIUM"

    else:
        return "LOW"


def _column_flag(df: pd.DataFrame, column: str, default: bool = True) -> bool:
    """A per-dataset (not per-row) availability flag stored as a
    constant column -- collapse it to a single bool."""

    if column not in df.columns or df.empty:
        return default

    return bool(df[column].iloc[0])


def determine_signal_availability(project_availability: dict, module_frames: dict) -> dict:
    return {
        "financial": bool(
            project_availability.get("sanctioned_amount")
            or project_availability.get("utilized_amount")
            or project_availability.get("released_amount")
        ),
        "delay": bool(
            project_availability.get("start_date")
            and project_availability.get("expected_completion_date")
        ),
        "progress": bool(
            project_availability.get("completion_percentage")
            and project_availability.get("financial_progress_ratio")
        ),
        "contractor": bool(project_availability.get("contractor")),
        "document": _column_flag(
            module_frames["document"], "document_signal_available", default=False
        ),
        "image": _column_flag(
            module_frames["image"], "image_signal_available", default=False
        ),
        "inspection": _column_flag(
            module_frames["inspection"], "inspection_signal_available", default=False
        ),
        "ml_anomaly": _column_flag(
            module_frames["ml_anomaly"], "ml_signal_available", default=False
        ),
        "duplicate": bool(project_availability.get("project_name")),
    }


def build_risk_fusion():

    print("\nLoading AI risk modules...")

    # ------------------------------------------------
    # 1. FINANCIAL ANALYSIS
    # ------------------------------------------------

    financial_df = detect_financial_anomalies()

    financial_scores = financial_df[
        ["project_id", "financial_anomaly", "financial_risk_score"]
    ].copy()

    # ------------------------------------------------
    # 2. DELAY ANALYSIS
    # ------------------------------------------------

    delay_df = detect_delays()

    delay_scores = delay_df[
        ["project_id", "delay_anomaly", "delay_risk_score"]
    ].copy()

    # ------------------------------------------------
    # 3. PROGRESS ANALYSIS
    # ------------------------------------------------

    progress_df = detect_progress_mismatch()

    progress_scores = progress_df[
        ["project_id", "progress_anomaly", "progress_risk_score"]
    ].copy()

    # ------------------------------------------------
    # 4. CONTRACTOR ANALYSIS
    # ------------------------------------------------

    contractor_df = calculate_contractor_risk()

    # Map contractor risk back to projects
    contractor_scores = financial_df[
        ["project_id", "contractor"]
    ].copy()

    contractor_scores = contractor_scores.merge(
        contractor_df[
            ["contractor", "contractor_risk_score"]
        ],
        on="contractor",
        how="left"
    )

    contractor_scores["contractor_risk_score"] = (
        contractor_scores["contractor_risk_score"]
        .fillna(0)
    )

    contractor_scores = contractor_scores[
        ["project_id", "contractor_risk_score"]
    ]

    # ------------------------------------------------
    # 5. DOCUMENT ANALYSIS
    # ------------------------------------------------

    document_df = verify_documents()

    document_scores = document_df[
        ["project_id", "document_anomaly", "document_risk_score"]
    ].copy()

    # ------------------------------------------------
    # 6. IMAGE ANALYSIS
    # ------------------------------------------------

    image_df = verify_images()

    image_scores = image_df[
        ["project_id", "image_anomaly", "image_risk_score"]
    ].copy()

    # ------------------------------------------------
    # 7. INSPECTION ANALYSIS
    # ------------------------------------------------

    inspection_df = analyze_inspections()

    inspection_scores = inspection_df[
        [
            "project_id",
            "inspection_anomaly",
            "inspection_risk_score"
        ]
    ].copy()

    # ------------------------------------------------
    # 8. ML ANOMALY DETECTION (Isolation Forest)
    # ------------------------------------------------

    ml_df = detect_ml_anomalies()

    ml_scores = ml_df[
        ["project_id", "ml_anomaly", "ml_anomaly_score", "ml_top_feature"]
    ].copy()

    # ------------------------------------------------
    # 9. DUPLICATE / RE-REGISTERED PROJECT DETECTION (TF-IDF)
    # ------------------------------------------------

    duplicate_scores = build_duplicate_risk()[
        ["project_id", "duplicate_anomaly", "duplicate_risk_score"]
    ].copy()

    # ------------------------------------------------
    # 10. MERGE ALL RISK SIGNALS
    # ------------------------------------------------

    risk_df = financial_df[
        [
            "project_id",
            "project_name",
            "state",
            "district",
            "mp_name",
            "project_type",
            "contractor",
            "agency",
            "status",
            "sanctioned_amount",
            "released_amount",
            "utilized_amount",
            "completion_percentage"
        ]
    ].copy()

    for scores in (
        financial_scores,
        delay_scores,
        progress_scores,
        contractor_scores,
        document_scores,
        image_scores,
        inspection_scores,
        ml_scores,
        duplicate_scores,
    ):
        risk_df = risk_df.merge(scores, on="project_id", how="left")

    # ------------------------------------------------
    # 11. HANDLE MISSING VALUES
    # ------------------------------------------------

    risk_columns = [
        "financial_risk_score",
        "delay_risk_score",
        "progress_risk_score",
        "contractor_risk_score",
        "document_risk_score",
        "image_risk_score",
        "inspection_risk_score",
        "ml_anomaly_score",
        "duplicate_risk_score",
    ]

    for column in risk_columns:

        risk_df[column] = pd.to_numeric(
            risk_df[column],
            errors="coerce"
        ).fillna(0)

    # ------------------------------------------------
    # 12. DETERMINE WHICH SIGNALS ARE AVAILABLE FOR
    #     THIS DATASET, AND RESCALE WEIGHTS OVER THEM
    # ------------------------------------------------

    project_availability = get_data_availability()

    availability = determine_signal_availability(
        project_availability,
        {
            "document": document_df,
            "image": image_df,
            "inspection": inspection_df,
            "ml_anomaly": ml_df,
        },
    )

    active_weight_total = sum(
        weight for signal, weight in SIGNAL_WEIGHTS.items() if availability[signal]
    )

    if active_weight_total <= 0:
        active_weight_total = 1.0

    effective_weights = {
        signal: (weight / active_weight_total if availability[signal] else 0.0)
        for signal, weight in SIGNAL_WEIGHTS.items()
    }

    score_column_by_signal = {
        "financial": "financial_risk_score",
        "delay": "delay_risk_score",
        "progress": "progress_risk_score",
        "contractor": "contractor_risk_score",
        "document": "document_risk_score",
        "image": "image_risk_score",
        "inspection": "inspection_risk_score",
        "ml_anomaly": "ml_anomaly_score",
        "duplicate": "duplicate_risk_score",
    }

    risk_df["overall_risk_score"] = 0.0

    for signal, weight in effective_weights.items():

        if weight <= 0:
            continue

        risk_df["overall_risk_score"] += (
            risk_df[score_column_by_signal[signal]] * weight
        )

    risk_df["overall_risk_score"] = (
        risk_df["overall_risk_score"]
        .clip(0, 100)
        .round(2)
    )

    # Signals that could not run at all for this dataset (e.g. no
    # documents.csv supplied) should never register as an "anomaly" --
    # there's nothing to flag, only something we couldn't check.
    for signal, column in [
        ("document", "document_anomaly"),
        ("image", "image_anomaly"),
        ("inspection", "inspection_anomaly"),
        ("ml_anomaly", "ml_anomaly"),
        ("duplicate", "duplicate_anomaly"),
    ]:
        if not availability[signal]:
            risk_df[column] = False

    # ------------------------------------------------
    # 13. RISK LEVEL
    # ------------------------------------------------

    risk_df["risk_level"] = (
        risk_df["overall_risk_score"]
        .apply(calculate_risk_level)
    )

    # ------------------------------------------------
    # 14. COUNT NUMBER OF RISK SIGNALS
    # ------------------------------------------------

    anomaly_columns = [
        "financial_anomaly",
        "delay_anomaly",
        "progress_anomaly",
        "document_anomaly",
        "image_anomaly",
        "inspection_anomaly",
        "ml_anomaly",
        "duplicate_anomaly",
    ]

    for column in anomaly_columns:

        risk_df[column] = (
            risk_df[column]
            .fillna(False)
            .astype(bool)
        )

    risk_df["risk_signal_count"] = (
        risk_df[anomaly_columns]
        .sum(axis=1)
    )

    risk_df.attrs["signal_availability"] = availability

    return risk_df


if __name__ == "__main__":

    df = build_risk_fusion()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("          RISK FUSION ENGINE")
    print("==========================================")

    print("\nSignal availability:", df.attrs.get("signal_availability"))

    print("\nTotal projects:", len(df))

    print("\nRisk distribution:")

    print(
        df["risk_level"]
        .value_counts()
        .to_string()
    )

    print("\nAverage risk score:",
          round(df["overall_risk_score"].mean(), 2))

    print(
        "\nHigh + Critical projects:",
        int(
            df["risk_level"]
            .isin(["HIGH", "CRITICAL"])
            .sum()
        )
    )

    print("\nTop 20 highest-risk projects:\n")

    columns = [
        "project_id",
        "project_name",
        "district",
        "contractor",
        "overall_risk_score",
        "risk_level",
        "risk_signal_count"
    ]

    print(
        df.sort_values(
            "overall_risk_score",
            ascending=False
        )[columns]
        .head(20)
        .to_string(index=False)
    )
