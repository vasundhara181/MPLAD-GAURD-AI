import pandas as pd
from pathlib import Path
from data_loader import get_active_data_dir, load_inspections, load_projects


BASE_DIR = Path(__file__).resolve().parent.parent
INSPECTION_FILE = BASE_DIR / "data" / "inspections.csv"


def generate_demo_inspections():
    """
    Generate synthetic inspection records for demonstration.
    """

    projects = load_projects().copy()

    inspections = []

    for index, project in projects.iterrows():

        project_id = str(project["project_id"])

        # Default inspection values
        inspection_score = 85
        inspection_status = "Passed"
        remarks = "Project inspection satisfactory"

        # Create some synthetic problematic inspections
        if index % 45 == 0:
            inspection_score = 35
            inspection_status = "Failed"
            remarks = "Work quality below expected standard"

        elif index % 60 == 0:
            inspection_score = 45
            inspection_status = "Needs Improvement"
            remarks = "Physical progress requires verification"

        elif index % 80 == 0:
            inspection_score = 25
            inspection_status = "Failed"
            remarks = "Project site requires detailed investigation"

        inspections.append({
            "inspection_id": f"INSP{index + 1:05d}",
            "project_id": project_id,
            "inspection_date": project["start_date"],
            "inspection_score": inspection_score,
            "inspection_status": inspection_status,
            "remarks": remarks
        })

    inspection_df = pd.DataFrame(inspections)

    inspection_df.to_csv(
        INSPECTION_FILE,
        index=False
    )

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("     INSPECTION DATA GENERATION")
    print("==========================================")

    print("\nInspection records generated:",
          len(inspection_df))

    print("\nSaved to:")
    print(INSPECTION_FILE)

    print("\nSample inspection records:\n")

    print(
        inspection_df.head(10)
        .to_string(index=False)
    )


def analyze_inspections():

    projects = load_projects().copy()

    projects["project_id"] = (
        projects["project_id"]
        .astype(str)
        .str.strip()
    )

    inspections = load_inspections()

    if inspections is None:
        # No inspection file was supplied for this dataset -- this
        # signal can't be evaluated.
        merged = projects.copy()
        merged["inspection_exists"] = False
        merged["missing_inspection"] = False
        merged["failed_inspection"] = False
        merged["needs_improvement"] = False
        merged["inspection_score"] = 0.0
        merged["low_inspection_score"] = False
        merged["inspection_anomaly"] = False
        merged["inspection_risk_score"] = 0.0
        merged["inspection_signal_available"] = False
        return merged

    # Merge project and inspection information
    merged = projects.merge(
        inspections,
        on="project_id",
        how="left"
    )

    # Check inspection existence
    merged["inspection_exists"] = (
        merged["inspection_id"].notna()
    )

    # Missing inspection
    merged["missing_inspection"] = (
        ~merged["inspection_exists"]
    )

    # Failed inspection
    merged["failed_inspection"] = (
        merged["inspection_status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .eq("failed")
    )

    # Needs improvement
    merged["needs_improvement"] = (
        merged["inspection_status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .eq("needs improvement")
    )

    # Low inspection score
    merged["low_inspection_score"] = (
        merged["inspection_score"] < 50
    )

    # Generate inspection risk score
    merged["inspection_anomaly"] = (
        merged["missing_inspection"]
        | merged["failed_inspection"]
        | merged["needs_improvement"]
        | merged["low_inspection_score"]
    )

    merged["inspection_risk_score"] = 0.0

    merged.loc[
        merged["missing_inspection"],
        "inspection_risk_score"
    ] += 30

    merged.loc[
        merged["failed_inspection"],
        "inspection_risk_score"
    ] += 50

    merged.loc[
        merged["needs_improvement"],
        "inspection_risk_score"
    ] += 25

    merged.loc[
        merged["low_inspection_score"],
        "inspection_risk_score"
    ] += 30

    merged["inspection_risk_score"] = (
        merged["inspection_risk_score"]
        .clip(upper=100)
    )

    merged["inspection_signal_available"] = True

    return merged


if __name__ == "__main__":

    # Generate synthetic inspection data
    generate_demo_inspections()

    # Analyze inspections
    df = analyze_inspections()

    anomalies = df[
        df["inspection_anomaly"]
    ].copy()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("       INSPECTION ANALYSIS")
    print("==========================================")

    print("\nTotal projects:",
          len(df))

    print(
        "Inspections available:",
        int(df["inspection_exists"].sum())
    )

    print(
        "Missing inspections:",
        int(df["missing_inspection"].sum())
    )

    print(
        "Failed inspections:",
        int(df["failed_inspection"].sum())
    )

    print(
        "Needs improvement:",
        int(df["needs_improvement"].sum())
    )

    print(
        "Low inspection scores:",
        int(df["low_inspection_score"].sum())
    )

    print(
        "\nInspection anomalies detected:",
        len(anomalies)
    )

    if len(anomalies) > 0:

        columns = [
            "project_id",
            "project_name",
            "inspection_id",
            "inspection_score",
            "inspection_status",
            "inspection_anomaly",
            "inspection_risk_score"
        ]

        print("\nTop inspection-risk projects:\n")

        print(
            anomalies
            .sort_values(
                "inspection_risk_score",
                ascending=False
            )[columns]
            .head(20)
            .to_string(index=False)
        )