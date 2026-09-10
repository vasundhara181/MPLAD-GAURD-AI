import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd
import json

from data_loader import (
    get_data_availability,
    is_using_default_dataset,
    load_projects,
    probe_dataset_files,
    reset_to_default_dataset,
    save_uploaded_dataset,
)
from citizen_feedback import (
    ALLOWED_CATEGORIES as CITIZEN_ALLOWED_CATEGORIES,
    get_citizen_reports,
    submit_citizen_report,
)
from geo_detection import detect_geo_anomalies
from insights import build_portfolio_insights
from schema import SIGNAL_REQUIREMENTS
from smart_alerts import build_smart_alerts
from verification import save_verification, get_verification_history


# ============================================================
# MPLAD-GUARD AI
# Main FastAPI Backend
# ============================================================

app = FastAPI(
    title="MPLAD-GUARD AI",
    description="AI-powered MPLADS Risk Intelligence Platform",
    version="1.0.0"
)


# ============================================================
# CORS CONFIGURATION
#
# Local dev origins always work. In production, set
# CORS_ALLOWED_ORIGINS to a comma-separated list of the deployed
# frontend URL(s), e.g. "https://mplad-guard.vercel.app".
# ============================================================

_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

_extra_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# VERIFICATION REQUEST MODEL
# ============================================================

class VerificationRequest(BaseModel):
    decision: str
    remarks: str = ""


class CitizenReportRequest(BaseModel):
    category: str
    description: str
    reporter_name: str = ""
    reporter_contact: str = ""


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():
    return {
        "message": "MPLAD-GUARD AI Backend is running",
        "system": "MPLAD-GUARD AI",
        "status": "online"
    }


# ============================================================
# HEALTH CHECK
# (used by Docker/Render/Railway to know the service is up)
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok"}


# ============================================================
# DATA READINESS
#
# Which of the 9 AI signals can actually run for whatever dataset
# is currently loaded (the bundled demo data, or an uploaded one).
# ============================================================

@app.get("/data-readiness")
def data_readiness():

    try:
        load_projects()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    project_availability = get_data_availability()
    dataset_files = probe_dataset_files()

    signals = {
        "financial": bool(
            project_availability.get("sanctioned_amount")
            or project_availability.get("utilized_amount")
            or project_availability.get("released_amount")
        ),
        "delay": bool(
            project_availability.get("start_date")
            and project_availability.get("expected_completion_date")
        ),
        "progress": bool(
            project_availability.get("completion_percentage")
            and project_availability.get("financial_progress_ratio")
        ),
        "contractor": bool(project_availability.get("contractor")),
        "document": dataset_files.get("documents", False),
        "image": dataset_files.get("images", False),
        "inspection": dataset_files.get("inspections", False),
        "ml_anomaly": bool(
            project_availability.get("completion_percentage")
            and project_availability.get("sanctioned_amount")
        ),
        "duplicate": bool(project_availability.get("project_name")),
        "geo": bool(
            project_availability.get("latitude")
            and project_availability.get("longitude")
        ),
        "citizen": True,
    }

    return {
        "using_default_dataset": is_using_default_dataset(),
        "dataset_files": dataset_files,
        "column_availability": project_availability,
        "signal_availability": signals,
        "signal_requirements": SIGNAL_REQUIREMENTS,
        "signals_available": sum(1 for available in signals.values() if available),
        "signals_total": len(signals),
    }


# ============================================================
# DATASET UPLOAD / RESET
#
# Swap in a different dataset at runtime -- proves the pipeline
# isn't hardcoded to the bundled synthetic CSVs. Only a projects
# file is required; documents/images/inspections are optional and
# unlock their matching signal when supplied.
# ============================================================

@app.post("/dataset/upload")
async def upload_dataset(
    projects: UploadFile = File(...),
    documents: UploadFile | None = File(None),
    images: UploadFile | None = File(None),
    inspections: UploadFile | None = File(None),
):

    files = {"projects": (projects.filename, await projects.read())}

    if documents is not None:
        files["documents"] = (documents.filename, await documents.read())

    if images is not None:
        files["images"] = (images.filename, await images.read())

    if inspections is not None:
        files["inspections"] = (inspections.filename, await inspections.read())

    try:
        save_uploaded_dataset(files)
        # Validate the new dataset actually loads before reporting success.
        load_projects()
    except ValueError as exc:
        reset_to_default_dataset()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        reset_to_default_dataset()
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the uploaded dataset: {exc}"
        )

    return data_readiness()


@app.post("/dataset/reset")
def reset_dataset():
    reset_to_default_dataset()
    return data_readiness()


# ============================================================
# GET ALL PROJECTS
# ============================================================

@app.get("/projects")
def get_projects():
    df = load_projects()

    records = df.to_json(
        orient="records",
        date_format="iso"
    )

    return json.loads(records)


# ============================================================
# COMPLETE RISK ANALYSIS
# ============================================================

@app.get("/risk-analysis")
def get_risk_analysis():
    df = build_smart_alerts()

    records = df.to_json(
        orient="records",
        date_format="iso"
    )

    return json.loads(records)


# ============================================================
# RISK SUMMARY
# ============================================================

@app.get("/risk-summary")
def get_risk_summary():

    df = build_smart_alerts()

    total_projects = len(df)

    low = int(
        (df["risk_level"] == "LOW").sum()
    )

    medium = int(
        (df["risk_level"] == "MEDIUM").sum()
    )

    high = int(
        (df["risk_level"] == "HIGH").sum()
    )

    critical = int(
        (df["risk_level"] == "CRITICAL").sum()
    )

    alerts = int(
        df["alert_required"].sum()
    )

    average_score = round(
        float(df["overall_risk_score"].mean()),
        2
    )

    return {
        "total_projects": total_projects,
        "low_risk": low,
        "medium_risk": medium,
        "high_risk": high,
        "critical_risk": critical,
        "total_alerts": alerts,
        "average_risk_score": average_score
    }


# ============================================================
# HIGH-RISK PROJECTS
# ============================================================

@app.get("/high-risk-projects")
def get_high_risk_projects():

    df = build_smart_alerts()

    high_risk = df[
        df["risk_level"].isin(
            ["HIGH", "CRITICAL"]
        )
    ].copy()

    high_risk = high_risk.sort_values(
        "overall_risk_score",
        ascending=False
    )

    columns = [
        "project_id",
        "project_name",
        "state",
        "district",
        "mp_name",
        "contractor",
        "overall_risk_score",
        "risk_level",
        "risk_signal_count",
        "priority",
        "alert_severity",
        "recommended_action"
    ]

    high_risk = high_risk[columns]

    records = high_risk.to_json(
        orient="records"
    )

    return json.loads(records)


# ============================================================
# SMART ALERTS
# ============================================================

@app.get("/alerts")
def get_alerts():

    df = build_smart_alerts()

    alerts = df[
        df["alert_required"] == True
    ].copy()

    alerts = alerts.sort_values(
        "overall_risk_score",
        ascending=False
    )

    columns = [
        "project_id",
        "project_name",
        "district",
        "overall_risk_score",
        "risk_level",
        "alert_type",
        "alert_severity",
        "priority",
        "recommended_action",
        "risk_reasons"
    ]

    alerts = alerts[columns]

    records = alerts.to_json(
        orient="records"
    )

    return json.loads(records)


# ============================================================
# PORTFOLIO AI INSIGHTS
#
# Fully automatic aggregate analysis over every project in the
# dataset -- no human verification required to produce this. This is
# the "complete overview" layer: which districts/contractors/project
# types concentrate risk, how much sanctioned money sits in
# HIGH/CRITICAL projects, and which of the 9 AI signals fires most
# often across the whole portfolio.
# ============================================================

@app.get("/insights")
def get_insights():
    return build_portfolio_insights()


# ============================================================
# GEO-SPATIAL PROJECT DATA
# ============================================================

@app.get("/map-projects")
def get_map_projects():

    # Original project data
    projects = load_projects().copy()

    # AI risk analysis
    risk_df = build_smart_alerts().copy()

    # Normalize project IDs
    projects["project_id"] = (
        projects["project_id"]
        .astype(str)
        .str.strip()
    )

    risk_df["project_id"] = (
        risk_df["project_id"]
        .astype(str)
        .str.strip()
    )

    # Risk fields required by map
    risk_columns = [
        "project_id",
        "overall_risk_score",
        "risk_level",
        "risk_signal_count",
        "geo_anomaly"
    ]

    risk_data = risk_df[
        risk_columns
    ].copy()

    # Merge coordinates with AI risk information
    df = projects.merge(
        risk_data,
        on="project_id",
        how="left"
    )

    # Convert coordinates
    df["latitude"] = pd.to_numeric(
        df["latitude"],
        errors="coerce"
    )

    df["longitude"] = pd.to_numeric(
        df["longitude"],
        errors="coerce"
    )

    # Remove projects without coordinates
    df = df[
        df["latitude"].notna()
        & df["longitude"].notna()
    ].copy()

    columns = [
        "project_id",
        "project_name",
        "state",
        "district",
        "latitude",
        "longitude",
        "overall_risk_score",
        "risk_level",
        "risk_signal_count",
        "geo_anomaly"
    ]

    df = df[columns]

    records = df.to_json(
        orient="records"
    )

    return json.loads(records)


# ============================================================
# INDIVIDUAL PROJECT INVESTIGATION
# ============================================================

@app.get("/project/{project_id}")
def get_project(project_id: str):

    df = build_smart_alerts().copy()

    # Normalize IDs
    df["project_id"] = (
        df["project_id"]
        .astype(str)
        .str.strip()
    )

    project_id = str(project_id).strip()

    project = df[
        df["project_id"] == project_id
    ]

    if project.empty:
        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    row = project.iloc[0]

    result = {

        # -------------------------------
        # Basic Information
        # -------------------------------

        "project_id":
            row.get("project_id"),

        "project_name":
            row.get("project_name"),

        "state":
            row.get("state"),

        "district":
            row.get("district"),

        "mp_name":
            row.get("mp_name"),

        "project_type":
            row.get("project_type"),

        "contractor":
            row.get("contractor"),

        "agency":
            row.get("agency"),

        "status":
            row.get("status"),


        # -------------------------------
        # Financial Information
        # -------------------------------

        "sanctioned_amount":
            row.get("sanctioned_amount", 0),

        "released_amount":
            row.get("released_amount", 0),

        "utilized_amount":
            row.get("utilized_amount", 0),


        # -------------------------------
        # Physical Progress
        # -------------------------------

        "completion_percentage":
            row.get(
                "completion_percentage",
                0
            ),


        # -------------------------------
        # Overall Risk
        # -------------------------------

        "overall_risk_score":
            row.get(
                "overall_risk_score",
                0
            ),

        "risk_level":
            row.get(
                "risk_level",
                "LOW"
            ),

        "risk_signal_count":
            row.get(
                "risk_signal_count",
                0
            ),

        "priority":
            row.get(
                "priority",
                "P5 - NORMAL"
            ),


        # -------------------------------
        # Individual Risk Scores
        # -------------------------------

        "financial_risk_score":
            row.get(
                "financial_risk_score",
                0
            ),

        "delay_risk_score":
            row.get(
                "delay_risk_score",
                0
            ),

        "progress_risk_score":
            row.get(
                "progress_risk_score",
                0
            ),

        "contractor_risk_score":
            row.get(
                "contractor_risk_score",
                0
            ),

        "document_risk_score":
            row.get(
                "document_risk_score",
                0
            ),

        "image_risk_score":
            row.get(
                "image_risk_score",
                0
            ),

        "inspection_risk_score":
            row.get(
                "inspection_risk_score",
                0
            ),

        "ml_anomaly_score":
            row.get(
                "ml_anomaly_score",
                0
            ),

        "duplicate_risk_score":
            row.get(
                "duplicate_risk_score",
                0
            ),

        "geo_risk_score":
            row.get(
                "geo_risk_score",
                0
            ),

        "geo_overlap_count":
            row.get(
                "geo_overlap_count",
                0
            ),

        "citizen_risk_score":
            row.get(
                "citizen_risk_score",
                0
            ),

        "citizen_report_count":
            row.get(
                "citizen_report_count",
                0
            ),


        # -------------------------------
        # Location
        # -------------------------------

        "latitude":
            row.get("latitude"),

        "longitude":
            row.get("longitude"),


        # -------------------------------
        # AI Recommendation
        # -------------------------------

        "recommended_action":
            row.get(
                "recommended_action",
                "Human verification recommended."
            ),

        "risk_reasons":
            row.get(
                "risk_reasons",
                []
            )
    }


    # ========================================================
    # Clean Pandas / NumPy values
    # ========================================================

    cleaned_result = {}

    for key, value in result.items():

        if value is None:

            cleaned_result[key] = None

        elif isinstance(value, float) and pd.isna(value):

            cleaned_result[key] = None

        elif hasattr(value, "item"):

            try:
                cleaned_result[key] = value.item()

            except Exception:
                cleaned_result[key] = value

        else:

            cleaned_result[key] = value

    return cleaned_result


# ============================================================
# HUMAN VERIFICATION
# ============================================================

@app.post("/project/{project_id}/verify")
def verify_project(
    project_id: str,
    request: VerificationRequest
):

    allowed_decisions = [
        "VERIFIED",
        "DISMISSED",
        "FIELD_INSPECTION",
        "ESCALATED"
    ]

    decision = (
        request.decision
        .upper()
        .strip()
    )

    # Validate decision
    if decision not in allowed_decisions:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid verification decision. "
                "Allowed values: "
                "VERIFIED, DISMISSED, "
                "FIELD_INSPECTION, ESCALATED"
            )
        )

    # Check whether project exists
    projects = load_projects()

    projects["project_id"] = (
        projects["project_id"]
        .astype(str)
        .str.strip()
    )

    if project_id not in set(
        projects["project_id"]
    ):

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    # Save human verification
    result = save_verification(
        project_id=project_id,
        decision=decision,
        remarks=request.remarks
    )

    return result


# ============================================================
# VERIFICATION HISTORY
# ============================================================

@app.get("/project/{project_id}/verification-history")
def verification_history(
    project_id: str
):

    # Check project exists
    projects = load_projects()

    projects["project_id"] = (
        projects["project_id"]
        .astype(str)
        .str.strip()
    )

    project_id = str(
        project_id
    ).strip()

    if project_id not in set(
        projects["project_id"]
    ):

        raise HTTPException(
            status_code=404,
            detail="Project not found"
        )

    return get_verification_history(
        project_id
    )


# ============================================================
# CITIZEN FEEDBACK
#
# Any citizen can report a concern against a project without an
# account. Reports are never taken as proven on their own -- they
# feed a capped, modest risk nudge and are always shown alongside
# the verified AI signals for a human to read directly.
# ============================================================

@app.post("/project/{project_id}/citizen-report")
def create_citizen_report(project_id: str, request: CitizenReportRequest):

    projects = load_projects()

    projects["project_id"] = projects["project_id"].astype(str).str.strip()
    project_id = str(project_id).strip()

    if project_id not in set(projects["project_id"]):
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = submit_citizen_report(
            project_id=project_id,
            category=request.category,
            description=request.description,
            reporter_name=request.reporter_name,
            reporter_contact=request.reporter_contact,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return result


@app.get("/project/{project_id}/citizen-reports")
def list_citizen_reports(project_id: str):

    projects = load_projects()

    projects["project_id"] = projects["project_id"].astype(str).str.strip()
    project_id = str(project_id).strip()

    if project_id not in set(projects["project_id"]):
        raise HTTPException(status_code=404, detail="Project not found")

    return get_citizen_reports(project_id)


@app.get("/citizen-report-categories")
def citizen_report_categories():
    return sorted(CITIZEN_ALLOWED_CATEGORIES)


# ============================================================
# GEO-SPATIAL OVERLAP PAIRS
#
# Exact project-location pairs whose sanctioned sites sit within
# 300m of each other -- used by the map to draw the overlap directly
# instead of only showing it as a per-project score.
# ============================================================

@app.get("/geo-overlaps")
def geo_overlaps():
    pairs = detect_geo_anomalies()

    records = pairs.to_json(orient="records")

    return json.loads(records)