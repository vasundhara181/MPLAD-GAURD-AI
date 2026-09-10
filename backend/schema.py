"""
Canonical data schema + header normalization.

Every risk module downstream assumes a fixed set of canonical column
names (see *_TEXT_DEFAULTS / *_NUMERIC_DEFAULTS / *_DATE_COLUMNS below).
Real-world datasets rarely use those exact header names, so this module:

1. Renames incoming headers to canonical names using a synonym table.
2. Falls back to fuzzy matching for anything still unrecognized.
3. Fills any canonical column that's still missing with a safe default
   (empty string / NaN / NaT) so downstream pandas code never raises
   KeyError on a dataset that doesn't look like our synthetic sample.

It also tracks, per canonical column, whether the value came from the
uploaded file or was synthesized as a default -- that's the basis of
the "data readiness" report shown in the UI.
"""

import re
from difflib import get_close_matches
from pathlib import Path

import pandas as pd

FUZZY_MATCH_CUTOFF = 0.78


def _normalize_key(name: str) -> str:
    key = str(name).strip().lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return key.strip("_")


def read_any_tabular(path_or_buffer, filename: str | None = None) -> pd.DataFrame:
    """Read a CSV or Excel file, deciding the format from the file name."""

    name = filename or getattr(path_or_buffer, "name", None) or str(path_or_buffer)
    suffix = Path(str(name)).suffix.lower()

    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(path_or_buffer)

    return pd.read_csv(path_or_buffer)


def normalize_headers(df: pd.DataFrame, synonyms: dict[str, list[str]]) -> pd.DataFrame:
    lookup = {}

    for canonical, alternates in synonyms.items():
        lookup[_normalize_key(canonical)] = canonical

        for alt in alternates:
            lookup[_normalize_key(alt)] = canonical

    rename_map = {}

    for column in df.columns:
        key = _normalize_key(column)

        if key in lookup:
            rename_map[column] = lookup[key]

    df = df.rename(columns=rename_map)

    # If renaming produced duplicate canonical columns, keep the first
    # non-empty one.
    df = df.loc[:, ~df.columns.duplicated()]

    return df


def fuzzy_fill_remaining(df: pd.DataFrame, canonical_columns: list[str]) -> pd.DataFrame:
    still_missing = [c for c in canonical_columns if c not in df.columns]

    if not still_missing:
        return df

    unclaimed = [c for c in df.columns if c not in canonical_columns]
    unclaimed_keys = {_normalize_key(c): c for c in unclaimed}

    rename_map = {}

    for canonical in still_missing:
        matches = get_close_matches(
            _normalize_key(canonical),
            unclaimed_keys.keys(),
            n=1,
            cutoff=FUZZY_MATCH_CUTOFF,
        )

        if matches:
            original_column = unclaimed_keys[matches[0]]
            rename_map[original_column] = canonical
            # Each raw column can only be claimed once.
            del unclaimed_keys[matches[0]]

    return df.rename(columns=rename_map)


def apply_defaults(
    df: pd.DataFrame,
    text_defaults: dict[str, str],
    numeric_defaults: dict[str, float],
    date_columns: list[str],
) -> tuple[pd.DataFrame, dict[str, bool]]:
    """Fill in any canonical column that's still absent, and report which
    canonical columns were genuinely present in the source file."""

    availability = {}

    for column in text_defaults:
        availability[column] = column in df.columns

        if column not in df.columns:
            df[column] = text_defaults[column]
        else:
            df[column] = df[column].fillna(text_defaults[column])

    for column, default in numeric_defaults.items():
        availability[column] = column in df.columns

        if column not in df.columns:
            df[column] = default
        else:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in date_columns:
        availability[column] = column in df.columns

        if column not in df.columns:
            df[column] = pd.NaT

    return df, availability


# =================================================================
# PROJECTS (projects.csv) SCHEMA
# =================================================================

PROJECT_REQUIRED_COLUMNS = ["project_id"]

PROJECT_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "project_id": ["proj_id", "id", "project_code", "scheme_id", "work_id"],
    "project_name": ["name", "project_title", "work_name", "title"],
    "state": ["state_name", "state_ut"],
    "district": ["district_name"],
    "mp_name": ["mp", "member_of_parliament", "mp_full_name", "member_name"],
    "project_type": ["work_type", "category", "scheme_type", "type"],
    "sanctioned_amount": [
        "sanctioned_amt", "amount_sanctioned", "sanction_amount", "sanctioned_amount_rs",
    ],
    "released_amount": ["released_amt", "amount_released", "fund_released"],
    "utilized_amount": [
        "utilized_amt", "amount_utilized", "expenditure", "amount_spent", "utilised_amount",
    ],
    "completion_percentage": [
        "physical_progress", "progress_percentage", "completion_pct", "physical_progress_percentage",
    ],
    "sanction_date": ["approval_date", "date_of_sanction"],
    "start_date": ["commencement_date", "work_start_date", "date_of_commencement"],
    "expected_completion_date": [
        "target_completion_date", "due_date", "expected_date_of_completion",
    ],
    "actual_completion_date": [
        "completion_date", "actual_end_date", "date_of_completion",
    ],
    "latitude": ["lat"],
    "longitude": ["lon", "lng"],
    "contractor": ["contractor_name", "vendor", "vendor_name", "agency_contractor"],
    "agency": ["implementing_agency", "executing_agency", "nodal_agency"],
    "status": ["project_status", "current_status", "work_status"],
    "financial_progress_ratio": ["financial_progress", "fund_utilization_ratio"],
}

PROJECT_TEXT_DEFAULTS = {
    "project_name": "",
    "state": "",
    "district": "",
    "mp_name": "",
    "project_type": "",
    "contractor": "Unknown",
    "agency": "",
    "status": "",
}

PROJECT_NUMERIC_DEFAULTS = {
    "sanctioned_amount": float("nan"),
    "released_amount": float("nan"),
    "utilized_amount": float("nan"),
    "completion_percentage": float("nan"),
    "financial_progress_ratio": float("nan"),
    "latitude": float("nan"),
    "longitude": float("nan"),
}

PROJECT_DATE_COLUMNS = [
    "sanction_date",
    "start_date",
    "expected_completion_date",
    "actual_completion_date",
]

PROJECT_CANONICAL_COLUMNS = (
    PROJECT_REQUIRED_COLUMNS
    + list(PROJECT_TEXT_DEFAULTS)
    + list(PROJECT_NUMERIC_DEFAULTS)
    + PROJECT_DATE_COLUMNS
)


def normalize_projects(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, bool]]:
    df = normalize_headers(df, PROJECT_COLUMN_SYNONYMS)
    df = fuzzy_fill_remaining(df, PROJECT_CANONICAL_COLUMNS)

    missing_required = [c for c in PROJECT_REQUIRED_COLUMNS if c not in df.columns]

    if missing_required:
        raise ValueError(
            "The uploaded project dataset is missing required column(s): "
            + ", ".join(missing_required)
            + ". At minimum a unique project identifier column is required."
        )

    df["project_id"] = df["project_id"].astype(str).str.strip()

    df, availability = apply_defaults(
        df, PROJECT_TEXT_DEFAULTS, PROJECT_NUMERIC_DEFAULTS, PROJECT_DATE_COLUMNS
    )

    availability["project_id"] = True

    return df, availability


# =================================================================
# DOCUMENTS (documents.csv) SCHEMA -- optional supplementary file
# =================================================================

DOCUMENT_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "document_id": ["doc_id"],
    "project_id": ["proj_id", "id", "project_code"],
    "document_type": ["doc_type", "type"],
    "amount": ["document_amount", "claimed_amount"],
    "contractor": ["contractor_name", "vendor"],
    "location": ["document_location", "site_location"],
    "extracted_text": ["ocr_text", "text", "description"],
    "status": ["document_status"],
}

DOCUMENT_TEXT_DEFAULTS = {
    "document_type": "",
    "contractor": "",
    "location": "",
    "extracted_text": "",
    "status": "",
}

DOCUMENT_NUMERIC_DEFAULTS = {
    "amount": float("nan"),
}

DOCUMENT_CANONICAL_COLUMNS = (
    ["document_id", "project_id"]
    + list(DOCUMENT_TEXT_DEFAULTS)
    + list(DOCUMENT_NUMERIC_DEFAULTS)
)


def normalize_documents(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_headers(df, DOCUMENT_COLUMN_SYNONYMS)
    df = fuzzy_fill_remaining(df, DOCUMENT_CANONICAL_COLUMNS)

    if "project_id" not in df.columns:
        raise ValueError("The documents file must have a project_id column.")

    df["project_id"] = df["project_id"].astype(str).str.strip()

    if "document_id" not in df.columns:
        df["document_id"] = range(1, len(df) + 1)

    df, _ = apply_defaults(df, DOCUMENT_TEXT_DEFAULTS, DOCUMENT_NUMERIC_DEFAULTS, [])

    return df


# =================================================================
# PROJECT IMAGES (project_images.csv) SCHEMA -- optional
# =================================================================

IMAGE_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "image_id": ["img_id"],
    "project_id": ["proj_id", "id", "project_code"],
    "image_hash": ["hash", "perceptual_hash", "phash"],
    "similarity_score": ["max_similarity", "similarity"],
    "status": ["image_status"],
}

IMAGE_TEXT_DEFAULTS = {
    "image_hash": "",
    "status": "",
}

IMAGE_NUMERIC_DEFAULTS = {
    "similarity_score": float("nan"),
}

IMAGE_CANONICAL_COLUMNS = (
    ["image_id", "project_id"]
    + list(IMAGE_TEXT_DEFAULTS)
    + list(IMAGE_NUMERIC_DEFAULTS)
)


def normalize_images(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_headers(df, IMAGE_COLUMN_SYNONYMS)
    df = fuzzy_fill_remaining(df, IMAGE_CANONICAL_COLUMNS)

    if "project_id" not in df.columns:
        raise ValueError("The project images file must have a project_id column.")

    df["project_id"] = df["project_id"].astype(str).str.strip()

    if "image_id" not in df.columns:
        df["image_id"] = range(1, len(df) + 1)

    df, _ = apply_defaults(df, IMAGE_TEXT_DEFAULTS, IMAGE_NUMERIC_DEFAULTS, [])

    return df


# =================================================================
# INSPECTIONS (inspections.csv) SCHEMA -- optional
# =================================================================

INSPECTION_COLUMN_SYNONYMS: dict[str, list[str]] = {
    "inspection_id": ["insp_id"],
    "project_id": ["proj_id", "id", "project_code"],
    "inspection_score": ["score", "quality_score"],
    "inspection_status": ["status", "result"],
    "remarks": ["comments", "notes"],
}

INSPECTION_TEXT_DEFAULTS = {
    "inspection_status": "",
    "remarks": "",
}

INSPECTION_NUMERIC_DEFAULTS = {
    "inspection_score": float("nan"),
}

INSPECTION_CANONICAL_COLUMNS = (
    ["inspection_id", "project_id"]
    + list(INSPECTION_TEXT_DEFAULTS)
    + list(INSPECTION_NUMERIC_DEFAULTS)
)


def normalize_inspections(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_headers(df, INSPECTION_COLUMN_SYNONYMS)
    df = fuzzy_fill_remaining(df, INSPECTION_CANONICAL_COLUMNS)

    if "project_id" not in df.columns:
        raise ValueError("The inspections file must have a project_id column.")

    df["project_id"] = df["project_id"].astype(str).str.strip()

    if "inspection_id" not in df.columns:
        df["inspection_id"] = range(1, len(df) + 1)

    df, _ = apply_defaults(df, INSPECTION_TEXT_DEFAULTS, INSPECTION_NUMERIC_DEFAULTS, [])

    return df


# =================================================================
# SIGNAL -> REQUIRED CANONICAL COLUMNS
# (used to build the data-readiness report)
# =================================================================

SIGNAL_REQUIREMENTS: dict[str, list[str]] = {
    "financial": ["sanctioned_amount", "utilized_amount", "released_amount"],
    "delay": ["start_date", "expected_completion_date"],
    "progress": ["completion_percentage", "financial_progress_ratio"],
    "contractor": ["contractor", "completion_percentage"],
    "document": ["__documents_file__"],
    "image": ["__images_file__"],
    "inspection": ["__inspections_file__"],
    "ml_anomaly": ["completion_percentage", "sanctioned_amount", "utilized_amount"],
    "duplicate": ["project_name"],
    "geo": ["latitude", "longitude"],
    "citizen": ["__always_available__"],
}
