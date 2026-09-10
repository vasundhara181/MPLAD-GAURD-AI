import pandas as pd
from data_loader import load_projects


def preprocess_projects():

    # Load the project dataset
    df = load_projects()

    # Convert date columns to datetime
    date_columns = [
        "sanction_date",
        "start_date",
        "expected_completion_date",
        "actual_completion_date"
    ]

    for column in date_columns:
        df[column] = pd.to_datetime(df[column], errors="coerce")

    # -------------------------------------------------
    # 1. Financial utilization percentage
    # -------------------------------------------------

    df["utilization_percentage"] = (
        df["utilized_amount"] / df["sanctioned_amount"]
    ) * 100

    # -------------------------------------------------
    # 2. Financial progress ratio
    # -------------------------------------------------

    df["financial_progress_percentage"] = (
        df["financial_progress_ratio"] * 100
    )

    # -------------------------------------------------
    # 3. Progress mismatch
    # -------------------------------------------------

    df["progress_mismatch"] = (
        df["financial_progress_percentage"]
        - df["completion_percentage"]
    )

    df["progress_mismatch_abs"] = df["progress_mismatch"].abs()

    # -------------------------------------------------
    # 4. Planned project duration
    # -------------------------------------------------

    df["planned_duration_days"] = (
        df["expected_completion_date"]
        - df["start_date"]
    ).dt.days

    # -------------------------------------------------
    # 5. Actual project duration
    # -------------------------------------------------

    today = pd.Timestamp.today().normalize()

    df["end_date_for_calculation"] = (
        df["actual_completion_date"].fillna(today)
    )

    df["actual_duration_days"] = (
        df["end_date_for_calculation"]
        - df["start_date"]
    ).dt.days

    # -------------------------------------------------
    # 6. Delay calculation
    # -------------------------------------------------

    df["delay_days"] = (
        df["end_date_for_calculation"]
        - df["expected_completion_date"]
    ).dt.days

    # Negative delay means the project is not delayed.
    df["delay_days"] = df["delay_days"].clip(lower=0)

    # -------------------------------------------------
    # 7. Missing data indicators
    # -------------------------------------------------

    df["missing_actual_completion"] = (
        df["actual_completion_date"].isna()
    )

    # -------------------------------------------------
    # 8. Replace infinite values
    # -------------------------------------------------

    df = df.replace([float("inf"), float("-inf")], pd.NA)

    return df


if __name__ == "__main__":

    df = preprocess_projects()

    print("\n======================================")
    print("MPLAD-GUARD AI")
    print("DATA PREPROCESSING")
    print("======================================")

    print("\nTotal projects:", len(df))

    print("\nNew AI features:")

    features = [
        "utilization_percentage",
        "financial_progress_percentage",
        "progress_mismatch",
        "progress_mismatch_abs",
        "planned_duration_days",
        "actual_duration_days",
        "delay_days",
        "missing_actual_completion"
    ]

    for feature in features:
        print(" -", feature)

    print("\nSample processed data:\n")

    print(
        df[
            [
                "project_id",
                "sanctioned_amount",
                "utilized_amount",
                "completion_percentage",
                "utilization_percentage",
                "progress_mismatch",
                "delay_days"
            ]
        ].head(10).to_string(index=False)
    )