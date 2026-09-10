import os
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_FILE = BASE_DIR / "data" / "verification_feedback.db"
DB_FILE = Path(os.environ.get("MPLAD_DB_FILE", DEFAULT_DB_FILE))

ALLOWED_DECISIONS = {"VERIFIED", "DISMISSED", "FIELD_INSPECTION", "ESCALATED"}


def _get_connection() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            remarks TEXT DEFAULT '',
            verified_by TEXT NOT NULL,
            verification_date TEXT NOT NULL
        )
        """
    )

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_verifications_project_id "
        "ON verifications(project_id)"
    )

    return conn


def save_verification(project_id: str, decision: str, remarks: str = ""):
    project_id = str(project_id).strip()
    verification_date = datetime.now().isoformat()
    verified_by = "Demo Officer"

    conn = _get_connection()

    try:
        conn.execute(
            """
            INSERT INTO verifications
                (project_id, decision, remarks, verified_by, verification_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, decision, remarks, verified_by, verification_date),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "success": True,
        "project_id": project_id,
        "decision": decision,
        "remarks": remarks,
        "verified_by": verified_by,
        "verification_date": verification_date,
    }


def get_verification_history(project_id: str):
    project_id = str(project_id).strip()

    conn = _get_connection()

    try:
        rows = conn.execute(
            """
            SELECT project_id, decision, remarks, verified_by, verification_date
            FROM verifications
            WHERE project_id = ?
            ORDER BY id ASC
            """,
            (project_id,),
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]
