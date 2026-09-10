"""
Citizen feedback integration.

A crowdsourced complementary signal: any citizen can report a concern
against a specific project (poor work quality, site inactivity,
suspected corruption, etc.) without needing an account. Reports are
never taken as proven fact on their own -- they feed a modest,
capped risk nudge (report volume, not content, since content isn't
independently verified) and are always shown alongside the AI signals
so a human reviewing a project can read them directly.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_FILE = BASE_DIR / "data" / "citizen_feedback.db"
DB_FILE = Path(os.environ.get("MPLAD_CITIZEN_DB_FILE", DEFAULT_DB_FILE))

ALLOWED_CATEGORIES = {
    "POOR_QUALITY",
    "PROJECT_INACTIVE",
    "SUSPECTED_CORRUPTION",
    "DOCUMENT_MISMATCH",
    "OTHER",
}

# Report-count -> risk score. Capped low relative to verified AI
# signals since unverified citizen reports are corroborating evidence,
# not proof.
MAX_CITIZEN_RISK_SCORE = 100
SCORE_PER_REPORT = 25


def _get_connection() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS citizen_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            reporter_name TEXT DEFAULT '',
            reporter_contact TEXT DEFAULT '',
            submitted_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_citizen_reports_project_id "
        "ON citizen_reports(project_id)"
    )

    return conn


def submit_citizen_report(
    project_id: str,
    category: str,
    description: str = "",
    reporter_name: str = "",
    reporter_contact: str = "",
) -> dict:
    project_id = str(project_id).strip()
    category = category.upper().strip()

    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"Invalid category. Allowed values: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    if not description.strip():
        raise ValueError("A description of the issue is required.")

    submitted_at = datetime.now().isoformat()

    conn = _get_connection()

    try:
        conn.execute(
            """
            INSERT INTO citizen_reports
                (project_id, category, description, reporter_name, reporter_contact, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, category, description.strip(), reporter_name.strip(), reporter_contact.strip(), submitted_at),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "project_id": project_id,
        "category": category,
        "description": description.strip(),
        "submitted_at": submitted_at,
    }


def get_citizen_reports(project_id: str) -> list:
    project_id = str(project_id).strip()

    conn = _get_connection()

    try:
        rows = conn.execute(
            """
            SELECT project_id, category, description, reporter_name, submitted_at
            FROM citizen_reports
            WHERE project_id = ?
            ORDER BY id DESC
            """,
            (project_id,),
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


def get_citizen_feedback_counts() -> dict:
    """project_id -> report count, for every project that has at least
    one report. Used both by the risk fusion signal and the insights
    'top districts by citizen reports' style views."""

    conn = _get_connection()

    try:
        rows = conn.execute(
            """
            SELECT project_id, COUNT(*) as report_count
            FROM citizen_reports
            GROUP BY project_id
            """
        ).fetchall()
    finally:
        conn.close()

    return {row["project_id"]: row["report_count"] for row in rows}


def citizen_report_to_score(report_count: int) -> float:
    return min(MAX_CITIZEN_RISK_SCORE, report_count * SCORE_PER_REPORT)


def citizen_feedback_fingerprint() -> str:
    """Cheap cache-invalidation key: changes whenever a report is added.
    Used by smart_alerts' cache so a new citizen report actually affects
    the next-computed risk score instead of waiting for the dataset
    cache to invalidate for an unrelated reason."""

    if not DB_FILE.exists():
        return "none"

    return str(DB_FILE.stat().st_mtime_ns)


if __name__ == "__main__":
    counts = get_citizen_feedback_counts()

    print("\n==========================================")
    print("          MPLAD-GUARD AI")
    print("      CITIZEN FEEDBACK SUMMARY")
    print("==========================================")

    print(f"\nProjects with at least one citizen report: {len(counts)}")

    for project_id, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]:
        print(f"  {project_id}: {count} report(s) -> risk contribution {citizen_report_to_score(count)}")
