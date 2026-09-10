import os
from pathlib import Path

import pandas as pd

from schema import (
    normalize_documents,
    normalize_images,
    normalize_inspections,
    normalize_projects,
    read_any_tabular,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = Path(os.environ.get("MPLAD_DATA_DIR", BASE_DIR / "data")).resolve()
UPLOAD_DIR = DEFAULT_DATA_DIR / "uploaded"

_active_data_dir = DEFAULT_DATA_DIR
_last_availability: dict = {}
_last_dataset_files: dict = {}


def get_active_data_dir() -> Path:
    return _active_data_dir


def set_active_data_dir(path) -> None:
    global _active_data_dir
    _active_data_dir = Path(path)


def reset_to_default_dataset() -> None:
    set_active_data_dir(DEFAULT_DATA_DIR)


def is_using_default_dataset() -> bool:
    return _active_data_dir == DEFAULT_DATA_DIR


def _find_file(directory: Path, stem_candidates: list[str]):
    for stem in stem_candidates:
        for suffix in (".csv", ".xlsx", ".xls"):
            candidate = directory / f"{stem}{suffix}"

            if candidate.exists():
                return candidate

    return None


def dataset_fingerprint() -> str:
    """A cheap cache key for 'what dataset is currently active, in what
    state'. Combines the active directory with each dataset file's
    modification time, so uploading a new file to the same path (the
    upload directory is reused across uploads) still invalidates any
    cache keyed on this value."""

    directory = get_active_data_dir()
    parts = [str(directory)]

    for stems in (["projects"], ["documents"], ["project_images", "images"], ["inspections"]):
        path = _find_file(directory, stems)

        if path is not None:
            parts.append(f"{path.name}:{path.stat().st_mtime_ns}")

    return "|".join(parts)


def load_projects() -> pd.DataFrame:
    directory = get_active_data_dir()
    path = _find_file(directory, ["projects"])

    if path is None:
        raise FileNotFoundError(
            f"No projects dataset found in {directory}. "
            "Upload a project dataset or check MPLAD_DATA_DIR."
        )

    raw = read_any_tabular(path)
    df, availability = normalize_projects(raw)

    _last_availability.update(availability)
    _last_dataset_files["projects"] = path.name

    return df


def load_documents():
    directory = get_active_data_dir()
    path = _find_file(directory, ["documents"])

    if path is None:
        _last_dataset_files["documents"] = None
        return None

    raw = read_any_tabular(path)
    df = normalize_documents(raw)
    _last_dataset_files["documents"] = path.name

    return df


def load_images():
    directory = get_active_data_dir()
    path = _find_file(directory, ["project_images", "images"])

    if path is None:
        _last_dataset_files["images"] = None
        return None

    raw = read_any_tabular(path)
    df = normalize_images(raw)
    _last_dataset_files["images"] = path.name

    return df


def load_inspections():
    directory = get_active_data_dir()
    path = _find_file(directory, ["inspections"])

    if path is None:
        _last_dataset_files["inspections"] = None
        return None

    raw = read_any_tabular(path)
    df = normalize_inspections(raw)
    _last_dataset_files["inspections"] = path.name

    return df


def probe_dataset_files() -> dict:
    """Direct filesystem check for which dataset files are present for
    the active dataset -- independent of whether a full risk
    computation has run yet in this process (unlike
    get_dataset_files(), which only reflects the last computation)."""

    directory = get_active_data_dir()

    return {
        "projects": _find_file(directory, ["projects"]) is not None,
        "documents": _find_file(directory, ["documents"]) is not None,
        "images": _find_file(directory, ["project_images", "images"]) is not None,
        "inspections": _find_file(directory, ["inspections"]) is not None,
    }


def get_data_availability() -> dict:
    """Which canonical project columns were genuinely present in the
    currently loaded dataset (vs synthesized as a default)."""

    return dict(_last_availability)


def get_dataset_files() -> dict:
    """Which supplementary files (documents/images/inspections) are
    present for the currently loaded dataset."""

    return dict(_last_dataset_files)


def save_uploaded_dataset(files: dict) -> Path:
    """Persist uploaded dataset file(s) and switch the active dataset to
    them. `files` maps canonical keys ('projects', 'documents', 'images',
    'inspections') to (filename, content_bytes) tuples. Only 'projects'
    is required -- anything else supplied unlocks the matching signal."""

    if "projects" not in files:
        raise ValueError("A projects file is required to switch datasets.")

    target_dir = UPLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # Clear out any previously uploaded dataset so stale files (e.g. an
    # old documents.csv) don't linger and get picked up unexpectedly.
    for existing in target_dir.glob("*"):
        existing.unlink()

    stem_by_key = {
        "projects": "projects",
        "documents": "documents",
        "images": "project_images",
        "inspections": "inspections",
    }

    for key, (filename, content) in files.items():
        suffix = Path(filename).suffix.lower() or ".csv"
        dest = target_dir / f"{stem_by_key.get(key, key)}{suffix}"
        dest.write_bytes(content)

    set_active_data_dir(target_dir)

    return target_dir


if __name__ == "__main__":
    df = load_projects()

    print("Dataset loaded successfully!")
    print("Number of projects:", len(df))

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nData availability:")
    print(get_data_availability())

    print("\nFirst 5 projects:")
    print(df.head())
