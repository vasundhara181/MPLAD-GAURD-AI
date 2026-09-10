# MPLAD-GUARD AI

AI-powered detection of anomalies, fraud, and inefficiencies in MPLAD Scheme
implementation. A FastAPI backend fuses 11 risk signals (rule-based, ML-based,
geo-spatial, and crowdsourced) per project into an explainable risk score,
fully automatically — no human review is required to generate it. A Next.js
frontend gives officers a real-time dashboard, portfolio-wide AI insights,
fund tracking, a geo-risk map with exact-location drill-down, and a
per-project investigation view with an optional human-in-the-loop
verification workflow and citizen feedback intake.

## Architecture

```
frontend/   Next.js 16 (App Router) dashboard + investigation UI
backend/    FastAPI risk-scoring API
data/       Bundled demo dataset (synthetic) + runtime SQLite DBs
```

## Key capabilities

- **Automated fraud detection** — 11 signals (below) run on every project
  automatically; nothing requires a human to trigger it.
- **Real-time fund tracking** — sanctioned/released/utilized totals,
  utilization rate, and unutilized-funds-at-risk, recomputed live from
  whatever dataset is loaded (`/insights`, "Real-Time Fund Tracking" panel).
- **Comprehensive data insights** — portfolio-wide breakdowns by district,
  contractor, and project type, plus AI-signal frequency across the whole
  dataset (the "Portfolio AI Insights" section) — not just a per-project score.
- **Scalable, dataset-agnostic infrastructure** — see below; a dataset-
  fingerprinted cache means the expensive pipeline (ML fit + similarity
  matrices) reruns only when the data actually changes, not on every request.
- **Geo-spatial anomaly detection** — vectorized haversine distance flags
  projects whose sanctioned locations sit within 1 km of another, unrelated
  project (a duplicate/split-billing pattern); shown as a dashed violet ring
  on the map and as an exact-pair list in Portfolio Insights.
- **Exact-location mapping** — every project's investigation page shows a
  zoomed-in map pinned to its precise coordinates, plus a direct
  "Open in Google Maps" link.
- **Risk prediction and scoring** — an Isolation Forest (scikit-learn) model
  flags statistical outliers a fixed threshold would miss, blended with the
  rule-based signals into one explainable 0-100 score.
- **Citizen feedback integration** — anyone can file an unverified report
  against a project (poor quality, inactivity, suspected corruption); report
  volume feeds a capped, supplementary risk signal and every report is shown
  to reviewing officers.

### The 11 risk signals

| Signal | Type | What it checks |
|---|---|---|
| Financial | Rule-based | Utilization/release vs. sanctioned amount |
| Delay | Rule-based | Schedule overrun vs. planned duration |
| Progress | Rule-based | Financial progress vs. physical completion mismatch |
| Contractor | Rule-based | Aggregate delay/mismatch history per contractor |
| Document | Rule-based | Sanction/utilization documents vs. project records |
| Image | Rule-based | Missing / reused / high-similarity site evidence photos |
| Inspection | Rule-based | Field inspection outcomes |
| **ML Anomaly** | **Isolation Forest (scikit-learn)** | Unsupervised outlier detection across utilization %, completion %, progress mismatch, and delay days — catches combinations a fixed threshold would miss |
| **Duplicate/Re-registered** | **TF-IDF + cosine similarity (scikit-learn)** | Flags projects whose name/type/district text closely matches another project — a classic split-billing pattern |
| **Geo-Spatial Overlap** | **Vectorized haversine distance (numpy)** | Flags projects whose exact sanctioned location sits within 1 km of another, unrelated project |
| **Citizen Feedback** | **Crowdsourced** | Report volume (not content, since it's unverified) against a project, capped at a modest contribution |

Each project's overall score is a weighted blend of whichever signals are
computable for the currently loaded dataset (see **Dataset-agnostic
ingestion** below) — weights automatically rescale to 100% over just the
available signals, so a partial dataset still produces a fair score instead
of one silently deflated by inputs that were never supplied. Citizen feedback
and geo-spatial checks are independent of the uploaded schema, so they're
always active.

### Dataset-agnostic ingestion

The backend does **not** assume the bundled synthetic CSV schema. `backend/schema.py`
normalizes incoming headers via a synonym table (e.g. `amt_sanctioned`,
`amount_sanctioned` → `sanctioned_amount`) with a fuzzy-match fallback, and
fills any still-missing optional column with a safe default instead of
crashing. Only a project-identifier column is truly required.

Use the **"Try your own dataset"** panel on the dashboard (or `POST
/dataset/upload`) to upload a different CSV/XLSX and watch the "Data
Readiness" chips show which of the 11 signals are active for it live —
`POST /dataset/reset` switches back to the bundled demo data.

## Local development

**Backend** (Python 3.12):
```bash
cd backend
python -m venv venv
./venv/Scripts/activate        # Windows; `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

**Frontend** (Node 20+):
```bash
cd frontend
npm install
cp .env.local.example .env.local   # defaults to http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000.

## Deploying

### Option A — Docker Compose (portable, works offline)

```bash
docker compose up --build
```
Frontend at http://localhost:3000, backend at http://localhost:8000. A named
volume (`mplad_data`) persists uploaded datasets and the verification
history database across restarts.

### Option B — Public cloud URL (Render + Vercel, free tiers)

**Backend on Render:**
1. Push this repo to GitHub.
2. In Render, "New +" → "Blueprint", point it at the repo — `render.yaml` at
   the repo root configures the service automatically (Docker runtime,
   `backend/Dockerfile`, health check at `/health`).
3. Note the deployed backend URL (e.g. `https://mplad-guard-ai-backend.onrender.com`).
4. Render's free plan has an ephemeral filesystem — an uploaded dataset or
   a recorded verification resets to the bundled demo data on redeploy/restart.
   That's fine for a demo; see `render.yaml` for how to add a persistent disk
   on a paid plan.

**Frontend on Vercel:**
1. Import the repo in Vercel, set the project root to `frontend/`.
2. Add an environment variable `NEXT_PUBLIC_API_URL` = your Render backend URL.
3. Deploy. Then set `CORS_ALLOWED_ORIGINS` on the Render service to your
   Vercel URL and redeploy the backend so the browser is allowed to call it.

## Known limitations (by design, for a hackathon-scope prototype)

- **SQLite for verification history** — fine for a single-instance demo;
  a multi-instance production deployment would need Postgres instead.
- **No auth** — anyone who can reach the API can upload a dataset or record
  a verification decision. Fine for a judged demo, not for a real deployment.
- **Free-tier disk is ephemeral** — see the Render note above.
- **Single-process cache** — the risk pipeline is cached in-process,
  keyed to the active dataset's file mtimes (and to the citizen-feedback
  DB's mtime, so a new report invalidates it too). This is correct and
  fast for a single `uvicorn` worker; a multi-worker/multi-instance
  production deployment would need a shared cache (Redis) instead, since
  each worker process currently has its own.
