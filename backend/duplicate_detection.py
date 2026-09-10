import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from data_loader import load_projects

# Calibrated against this project's own synthetic ground-truth "duplicate"
# scenario: genuine injected duplicates score 0.56-0.66 on name+type text
# (district excluded -- see below), normal projects average ~0.39 with a
# long tail, and only ~1.7% of normal projects cross 0.55 by coincidence.
# 0.80 (the original guess) caught zero of the 15 known duplicates.
SIMILARITY_THRESHOLD = 0.55
MIN_ROWS_TO_RUN = 5


def detect_similar_projects() -> pd.DataFrame:
    """Pairwise TF-IDF + cosine similarity over project name/type text,
    vectorized (no Python-level double loop) so it stays fast even at a
    few thousand rows."""

    df = load_projects().copy()

    if len(df) < MIN_ROWS_TO_RUN:
        return pd.DataFrame(
            columns=[
                "project_id_1", "project_name_1",
                "project_id_2", "project_name_2",
                "similarity_score",
            ]
        )

    # District is deliberately excluded: two unrelated projects that
    # happen to share a project_type and district (common at 1,000+ rows
    # across ~30 districts) otherwise inflate similarity enough to blur
    # into genuine duplicates -- name + type alone separates the two
    # populations far more cleanly.
    text = (
        df["project_name"].fillna("").astype(str)
        + " "
        + df["project_type"].fillna("").astype(str)
    )

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(text)

    similarity_matrix = cosine_similarity(tfidf_matrix)

    n = len(df)
    upper_i, upper_j = np.triu_indices(n, k=1)
    scores = similarity_matrix[upper_i, upper_j]

    mask = scores >= SIMILARITY_THRESHOLD

    project_ids = df["project_id"].to_numpy()
    project_names = df["project_name"].to_numpy()

    duplicate_df = pd.DataFrame({
        "project_id_1": project_ids[upper_i[mask]],
        "project_name_1": project_names[upper_i[mask]],
        "project_id_2": project_ids[upper_j[mask]],
        "project_name_2": project_names[upper_j[mask]],
        "similarity_score": np.round(scores[mask], 3),
    })

    return duplicate_df


def build_duplicate_risk() -> pd.DataFrame:
    """Per-project duplicate signal for the risk fusion pipeline: does
    this project have a near-duplicate name/type/district elsewhere in
    the portfolio (a classic split-billing / re-registered-project
    pattern)?"""

    projects = load_projects().copy()
    pairs = detect_similar_projects()

    result = projects[["project_id"]].copy()

    if pairs.empty:
        result["duplicate_anomaly"] = False
        result["duplicate_risk_score"] = 0.0
        result["duplicate_match_score"] = 0.0
        return result

    best_match = pd.concat(
        [
            pairs[["project_id_1", "similarity_score"]].rename(
                columns={"project_id_1": "project_id"}
            ),
            pairs[["project_id_2", "similarity_score"]].rename(
                columns={"project_id_2": "project_id"}
            ),
        ],
        ignore_index=True,
    ).groupby("project_id")["similarity_score"].max()

    result["duplicate_match_score"] = (
        result["project_id"].map(best_match).fillna(0.0)
    )

    result["duplicate_anomaly"] = result["duplicate_match_score"] > 0

    result["duplicate_risk_score"] = (
        (result["duplicate_match_score"] * 100)
        .clip(upper=100)
        .round(2)
    )

    return result


if __name__ == "__main__":
    duplicate_df = detect_similar_projects()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("    DUPLICATE PROJECT DETECTION")
    print("==========================================")

    print("\nPotentially similar project pairs:", len(duplicate_df))

    if len(duplicate_df) > 0:
        print(
            "\nTop similar projects:\n",
            duplicate_df.sort_values("similarity_score", ascending=False)
            .head(20)
            .to_string(index=False),
        )
    else:
        print("\nNo projects crossed the similarity threshold.")
