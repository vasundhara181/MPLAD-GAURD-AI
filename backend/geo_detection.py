"""
Geo-spatial anomaly detection.

Flags projects whose sanctioned location sits suspiciously close to
another, unrelated project -- a classic real-world MPLAD fraud pattern
(the same physical site claimed/geotagged for multiple sanctioned
works, or a project relocated on paper without an actual site change).
Distance matrix is computed vectorized (numpy), not a Python double
loop, so it stays fast at real dataset sizes.
"""

import numpy as np
import pandas as pd

from data_loader import load_projects

EARTH_RADIUS_KM = 6371.0

# Projects legitimately cluster within a few km of each other inside
# the same district -- that's normal, not suspicious. 300m is closer
# to "same site" than "same town", which is the actual fraud pattern
# this is meant to catch (two sanctioned works claiming the same
# physical location).
OVERLAP_THRESHOLD_KM = 0.3
MIN_ROWS_TO_RUN = 5


def _haversine_distance_matrix(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)

    dlat = lat_rad[:, None] - lat_rad[None, :]
    dlon = lon_rad[:, None] - lon_rad[None, :]

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat_rad)[:, None] * np.cos(lat_rad)[None, :] * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    return EARTH_RADIUS_KM * c


def detect_geo_anomalies() -> pd.DataFrame:
    """Pairwise list of project pairs whose sanctioned locations sit
    within OVERLAP_THRESHOLD_KM of each other."""

    df = load_projects().copy()

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    valid = df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)

    if len(valid) < MIN_ROWS_TO_RUN:
        return pd.DataFrame(
            columns=[
                "project_id_1", "project_name_1",
                "project_id_2", "project_name_2",
                "distance_km",
            ]
        )

    distances = _haversine_distance_matrix(
        valid["latitude"].to_numpy(), valid["longitude"].to_numpy()
    )

    n = len(valid)
    upper_i, upper_j = np.triu_indices(n, k=1)
    pair_distances = distances[upper_i, upper_j]

    mask = pair_distances <= OVERLAP_THRESHOLD_KM

    project_ids = valid["project_id"].to_numpy()
    project_names = valid["project_name"].to_numpy()

    nearby_df = pd.DataFrame({
        "project_id_1": project_ids[upper_i[mask]],
        "project_name_1": project_names[upper_i[mask]],
        "project_id_2": project_ids[upper_j[mask]],
        "project_name_2": project_names[upper_j[mask]],
        "distance_km": np.round(pair_distances[mask], 3),
    })

    return nearby_df


def build_geo_risk() -> pd.DataFrame:
    """Per-project geo-overlap signal for the risk fusion pipeline:
    does this project's location sit suspiciously close to another,
    unrelated project?"""

    projects = load_projects().copy()
    pairs = detect_geo_anomalies()

    result = projects[["project_id"]].copy()

    if pairs.empty:
        result["geo_anomaly"] = False
        result["geo_risk_score"] = 0.0
        result["geo_overlap_count"] = 0
        result["geo_nearest_km"] = np.nan
        return result

    long_pairs = pd.concat(
        [
            pairs[["project_id_1", "distance_km"]].rename(columns={"project_id_1": "project_id"}),
            pairs[["project_id_2", "distance_km"]].rename(columns={"project_id_2": "project_id"}),
        ],
        ignore_index=True,
    )

    stats = long_pairs.groupby("project_id")["distance_km"].agg(["min", "count"])
    stats.columns = ["geo_nearest_km", "geo_overlap_count"]

    result = result.merge(stats, on="project_id", how="left")

    result["geo_overlap_count"] = result["geo_overlap_count"].fillna(0).astype(int)
    result["geo_anomaly"] = result["geo_overlap_count"] > 0

    # Closer + more overlapping neighbours = higher risk.
    closeness = (
        (OVERLAP_THRESHOLD_KM - result["geo_nearest_km"].fillna(OVERLAP_THRESHOLD_KM))
        / OVERLAP_THRESHOLD_KM
    ).clip(lower=0)

    multiplicity_bonus = result["geo_overlap_count"].clip(upper=3) * 10

    result["geo_risk_score"] = (
        (closeness * 70 + multiplicity_bonus).clip(upper=100).round(2)
    )

    result.loc[~result["geo_anomaly"], "geo_risk_score"] = 0.0

    return result


if __name__ == "__main__":
    nearby_df = detect_geo_anomalies()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("      GEO-SPATIAL ANALYSIS")
    print("==========================================")

    print("\nPotentially overlapping/nearby project pairs:", len(nearby_df))

    if len(nearby_df) > 0:
        print(
            "\nClosest project pairs:\n",
            nearby_df.sort_values("distance_km").head(20).to_string(index=False),
        )
    else:
        print("\nNo nearby project pairs found.")
