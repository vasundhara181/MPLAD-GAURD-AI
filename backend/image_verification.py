import pandas as pd

from data_loader import load_images, load_projects


def verify_images():

    # ---------------------------------------------
    # 1. Load project and image data
    # ---------------------------------------------

    projects = load_projects().copy()

    projects["project_id"] = (
        projects["project_id"]
        .astype(str)
        .str.strip()
    )

    images = load_images()

    if images is None:
        # No image evidence file was supplied for this dataset --
        # this signal can't be evaluated.
        merged = projects.copy()
        merged["image_exists"] = False
        merged["missing_image"] = False
        merged["reused_image"] = False
        merged["similarity_score"] = 0.0
        merged["high_similarity"] = False
        merged["potentially_reused"] = False
        merged["image_anomaly"] = False
        merged["image_risk_score"] = 0.0
        merged["image_signal_available"] = False
        return merged

    # ---------------------------------------------
    # 3. Merge project and image information
    # ---------------------------------------------

    merged = projects.merge(
        images,
        on="project_id",
        how="left",
        suffixes=("_project", "_image")
    )

    # ---------------------------------------------
    # 4. Check whether image exists
    # ---------------------------------------------

    merged["image_exists"] = (
        merged["image_id"].notna()
    )

    # ---------------------------------------------
    # 5. Missing image
    # ---------------------------------------------

    merged["missing_image"] = (
        ~merged["image_exists"]
    )

    # ---------------------------------------------
    # 6. Detect reused image hashes
    # ---------------------------------------------

    image_hash_counts = (
        images["image_hash"]
        .dropna()
        .astype(str)
        .value_counts()
    )

    merged["reused_image"] = (
        merged["image_hash"]
        .astype("string")
        .map(image_hash_counts)
        .fillna(0)
        > 1
    )

    # Only mark reused images when an image exists
    merged["reused_image"] = (
        merged["reused_image"]
        & merged["image_exists"]
    )

    # ---------------------------------------------
    # 7. Convert similarity score
    # ---------------------------------------------

    merged["similarity_score"] = pd.to_numeric(
        merged["similarity_score"],
        errors="coerce"
    ).fillna(0)

    # ---------------------------------------------
    # 8. High similarity
    # ---------------------------------------------

    merged["high_similarity"] = (
        merged["similarity_score"] >= 0.90
    )

    # ---------------------------------------------
    # 9. Potentially reused status
    # ---------------------------------------------

    # IMPORTANT:
    # Because both projects and images have a
    # status column, after merging the image status
    # is called status_image.

    image_status = (
        merged["status_image"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    merged["potentially_reused"] = (
        image_status.str.contains(
            "reused",
            regex=False
        )
    )

    # ---------------------------------------------
    # 10. Overall image anomaly
    # ---------------------------------------------

    merged["image_anomaly"] = (
        merged["missing_image"]
        |
        merged["reused_image"]
        |
        merged["high_similarity"]
        |
        merged["potentially_reused"]
    )

    # ---------------------------------------------
    # 11. Image risk score
    # ---------------------------------------------

    merged["image_risk_score"] = 0.0

    merged.loc[
        merged["missing_image"],
        "image_risk_score"
    ] += 30

    merged.loc[
        merged["reused_image"],
        "image_risk_score"
    ] += 50

    merged.loc[
        merged["high_similarity"],
        "image_risk_score"
    ] += 30

    merged.loc[
        merged["potentially_reused"],
        "image_risk_score"
    ] += 20

    # Maximum score = 100
    merged["image_risk_score"] = (
        merged["image_risk_score"]
        .clip(upper=100)
    )

    merged["image_signal_available"] = True

    return merged


# =============================================
# Run directly
# =============================================

if __name__ == "__main__":

    df = verify_images()

    anomalies = df[
        df["image_anomaly"]
    ].copy()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("        IMAGE VERIFICATION")
    print("==========================================")

    print(
        "\nTotal projects:",
        len(df)
    )

    print(
        "Images available:",
        int(df["image_exists"].sum())
    )

    print(
        "Missing images:",
        int(df["missing_image"].sum())
    )

    print(
        "Reused images:",
        int(df["reused_image"].sum())
    )

    print(
        "High-similarity images:",
        int(df["high_similarity"].sum())
    )

    print(
        "Potentially reused status:",
        int(df["potentially_reused"].sum())
    )

    print(
        "\nImage anomalies detected:",
        len(anomalies)
    )

    if len(anomalies) > 0:

        print("\nTop image-risk projects:\n")

        columns = [
            "project_id",
            "project_name",
            "image_id",
            "missing_image",
            "reused_image",
            "high_similarity",
            "similarity_score",
            "image_risk_score"
        ]

        print(
            anomalies
            .sort_values(
                "image_risk_score",
                ascending=False
            )
            [columns]
            .head(20)
            .to_string(index=False)
        )