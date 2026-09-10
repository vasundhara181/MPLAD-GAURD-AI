import pandas as pd
from data_loader import load_projects


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two geographic coordinates.
    Returns distance in kilometers.
    """

    import math

    R = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


def detect_geo_anomalies():

    df = load_projects().copy()

    # Convert coordinates to numeric
    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    nearby_pairs = []

    # Distance threshold
    # Projects within 1 km will be considered
    # potentially overlapping/nearby.
    threshold_km = 1.0

    for i in range(len(df)):

        lat1 = df.iloc[i]["latitude"]
        lon1 = df.iloc[i]["longitude"]

        if pd.isna(lat1) or pd.isna(lon1):
            continue

        for j in range(i + 1, len(df)):

            lat2 = df.iloc[j]["latitude"]
            lon2 = df.iloc[j]["longitude"]

            if pd.isna(lat2) or pd.isna(lon2):
                continue

            distance = haversine_distance(
                lat1,
                lon1,
                lat2,
                lon2
            )

            if distance <= threshold_km:

                nearby_pairs.append({
                    "project_id_1":
                        df.iloc[i]["project_id"],

                    "project_name_1":
                        df.iloc[i]["project_name"],

                    "project_id_2":
                        df.iloc[j]["project_id"],

                    "project_name_2":
                        df.iloc[j]["project_name"],

                    "distance_km":
                        round(distance, 3)
                })

    nearby_df = pd.DataFrame(nearby_pairs)

    return nearby_df


if __name__ == "__main__":

    nearby_df = detect_geo_anomalies()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("      GEO-SPATIAL ANALYSIS")
    print("==========================================")

    print(
        "\nPotentially overlapping/nearby project pairs:",
        len(nearby_df)
    )

    if len(nearby_df) > 0:

        print("\nClosest project pairs:\n")

        print(
            nearby_df
            .sort_values(
                "distance_km"
            )
            .head(20)
            .to_string(index=False)
        )

    else:

        print(
            "\nNo nearby project pairs found."
        )