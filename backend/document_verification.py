import pandas as pd

from data_loader import load_documents, load_projects


def verify_documents():

    # ---------------------------------------------
    # 1. Load project and document data
    # ---------------------------------------------

    projects = load_projects().copy()

    projects["project_id"] = (
        projects["project_id"]
        .astype(str)
        .str.strip()
    )

    documents = load_documents()

    if documents is None:
        # No documents file was supplied for this dataset at all --
        # this signal can't be evaluated, so report it as unavailable
        # rather than flagging every project as "missing a document".
        merged = projects.copy()
        merged["document_exists"] = False
        merged["amount_mismatch"] = False
        merged["contractor_mismatch"] = False
        merged["location_mismatch"] = False
        merged["missing_document"] = False
        merged["document_anomaly"] = False
        merged["document_risk_score"] = 0.0
        merged["document_signal_available"] = False
        return merged

    # ---------------------------------------------
    # 3. Merge projects with documents
    # ---------------------------------------------

    merged = projects.merge(
        documents,
        on="project_id",
        how="left",
        suffixes=("_project", "_document")
    )

    # ---------------------------------------------
    # 4. Check whether a document exists
    # ---------------------------------------------

    merged["document_exists"] = (
        merged["document_id"].notna()
    )

    # ---------------------------------------------
    # 5. Amount mismatch
    # ---------------------------------------------

    merged["utilized_amount"] = pd.to_numeric(
        merged["utilized_amount"],
        errors="coerce"
    )

    merged["amount"] = pd.to_numeric(
        merged["amount"],
        errors="coerce"
    )

    merged["amount_mismatch"] = False

    amount_available = (
        merged["document_exists"]
        & merged["amount"].notna()
        & merged["utilized_amount"].notna()
    )

    merged.loc[amount_available, "amount_mismatch"] = (
        (
            merged.loc[amount_available, "amount"]
            -
            merged.loc[amount_available, "utilized_amount"]
        ).abs() > 1
    )

    # ---------------------------------------------
    # 6. Contractor mismatch
    # ---------------------------------------------

    project_contractor = (
        merged["contractor_project"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    document_contractor = (
        merged["contractor_document"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    merged["contractor_mismatch"] = (
        merged["document_exists"]
        &
        (project_contractor != document_contractor)
    )

    # ---------------------------------------------
    # 7. Location mismatch
    # ---------------------------------------------

    project_district = (
        merged["district"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    document_location = (
        merged["location"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    merged["location_mismatch"] = False

    # Compare each project's district with its
    # corresponding document location.
    for i in merged.index:

        if not merged.loc[i, "document_exists"]:
            continue

        district = project_district.loc[i]
        location = document_location.loc[i]

        if district == "" or location == "":
            continue

        if district not in location:
            merged.loc[i, "location_mismatch"] = True

    # ---------------------------------------------
    # 8. Missing document
    # ---------------------------------------------

    merged["missing_document"] = (
        ~merged["document_exists"]
    )

    # ---------------------------------------------
    # 9. Overall document anomaly
    # ---------------------------------------------

    merged["document_anomaly"] = (
        merged["amount_mismatch"]
        |
        merged["contractor_mismatch"]
        |
        merged["location_mismatch"]
        |
        merged["missing_document"]
    )

    # ---------------------------------------------
    # 10. Document risk score
    # ---------------------------------------------

    merged["document_risk_score"] = 0.0

    merged.loc[
        merged["amount_mismatch"],
        "document_risk_score"
    ] += 40

    merged.loc[
        merged["contractor_mismatch"],
        "document_risk_score"
    ] += 30

    merged.loc[
        merged["location_mismatch"],
        "document_risk_score"
    ] += 20

    merged.loc[
        merged["missing_document"],
        "document_risk_score"
    ] += 30

    # Maximum score = 100
    merged["document_risk_score"] = (
        merged["document_risk_score"]
        .clip(upper=100)
    )

    merged["document_signal_available"] = True

    return merged


# =============================================
# Run directly
# =============================================

if __name__ == "__main__":

    df = verify_documents()

    anomalies = df[
        df["document_anomaly"]
    ].copy()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("       DOCUMENT VERIFICATION")
    print("==========================================")

    print(
        "\nTotal projects:",
        len(df)
    )

    print(
        "Documents available:",
        int(df["document_exists"].sum())
    )

    print(
        "Missing documents:",
        int(df["missing_document"].sum())
    )

    print(
        "\nDocument anomalies detected:",
        len(anomalies)
    )

    print(
        "\nAmount mismatches:",
        int(df["amount_mismatch"].sum())
    )

    print(
        "Contractor mismatches:",
        int(df["contractor_mismatch"].sum())
    )

    print(
        "Location mismatches:",
        int(df["location_mismatch"].sum())
    )

    if len(anomalies) > 0:

        print("\nTop document-risk projects:\n")

        columns = [
            "project_id",
            "project_name",
            "document_id",
            "amount_mismatch",
            "contractor_mismatch",
            "location_mismatch",
            "missing_document",
            "document_risk_score"
        ]

        print(
            anomalies
            .sort_values(
                "document_risk_score",
                ascending=False
            )
            [columns]
            .head(20)
            .to_string(index=False)
        )