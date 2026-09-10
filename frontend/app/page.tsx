"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] w-full rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-slate-500">
      Loading map...
    </div>
  ),
});

type RiskSummary = {
  total_projects: number;
  low_risk: number;
  medium_risk: number;
  high_risk: number;
  critical_risk: number;
  total_alerts: number;
  average_risk_score: number;
};

type MapProject = {
  project_id: string;
  project_name: string;
  state: string;
  district: string;
  latitude: number;
  longitude: number;
  overall_risk_score: number;
  risk_level: string;
  risk_signal_count: number;
  geo_anomaly: boolean;
};

type RiskProject = {
  project_id: string;
  project_name: string;
  state: string;
  district: string;
  mp_name: string;
  contractor: string;
  overall_risk_score: number;
  risk_level: string;
  risk_signal_count: number;
  priority: string;
  alert_severity: string;
  recommended_action: string;
};

type DataReadiness = {
  using_default_dataset: boolean;
  dataset_files: Record<string, boolean>;
  signal_availability: Record<string, boolean>;
  signals_available: number;
  signals_total: number;
};

type RiskGroup = {
  name: string;
  project_count: number;
  average_risk_score: number;
  high_or_critical_count: number;
  sanctioned_amount_at_risk: number;
};

type SignalFrequency = {
  signal: string;
  flagged_projects: number;
  percentage: number;
};

type StatusCount = {
  status: string;
  count: number;
  percentage: number;
};

type FundTracking = {
  total_sanctioned: number;
  total_released: number;
  total_utilized: number;
  unutilized_funds: number;
  utilization_rate_percentage: number;
  release_rate_percentage: number;
};

type GeoOverlapPair = {
  project_id_1: string;
  project_name_1: string;
  project_id_2: string;
  project_name_2: string;
  distance_km: number;
};

type Insights = {
  total_projects: number;
  flagged_projects: number;
  flagged_percentage: number;
  total_sanctioned_amount: number;
  sanctioned_amount_at_risk: number;
  sanctioned_at_risk_percentage: number;
  status_breakdown: StatusCount[];
  fund_tracking: FundTracking;
  geo_overlap_pairs: GeoOverlapPair[];
  signal_frequency: SignalFrequency[];
  risk_by_district: RiskGroup[];
  risk_by_contractor: RiskGroup[];
  risk_by_project_type: RiskGroup[];
};

type AlertItem = {
  project_id: string;
  project_name: string;
  district: string;
  overall_risk_score: number;
  risk_level: string;
  alert_type: string;
  alert_severity: string;
  priority: string;
  recommended_action: string;
  risk_reasons: string[];
};

const SIGNAL_LABELS: Record<string, string> = {
  financial: "Financial",
  delay: "Delay",
  progress: "Progress",
  contractor: "Contractor",
  document: "Document",
  image: "Image",
  inspection: "Inspection",
  ml_anomaly: "ML Anomaly",
  duplicate: "Duplicate",
  geo: "Geo-Spatial",
  citizen: "Citizen Feedback",
};

const RISK_LEVELS = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

function riskBadgeClass(level: string) {
  switch (level) {
    case "CRITICAL":
      return "bg-red-50 text-red-700 border-red-200";
    case "HIGH":
      return "bg-orange-50 text-orange-700 border-orange-200";
    case "MEDIUM":
      return "bg-yellow-50 text-yellow-700 border-yellow-200";
    default:
      return "bg-green-50 text-green-700 border-green-200";
  }
}

function formatCurrency(value: number) {
  if (!Number.isFinite(value)) return "₹0";
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}

function statusMeta(status: string): {
  icon: string;
  className: string;
} {
  switch (status.toLowerCase()) {
    case "completed":
      return { icon: "✅", className: "bg-green-50 text-green-700 border-green-200" };
    case "in progress":
      return { icon: "🔄", className: "bg-blue-50 text-blue-700 border-blue-200" };
    case "delayed":
      return { icon: "⏳", className: "bg-orange-50 text-orange-700 border-orange-200" };
    case "not started":
      return { icon: "⭕", className: "bg-slate-100 text-slate-700 border-slate-300" };
    default:
      return { icon: "❔", className: "bg-slate-100 text-slate-700 border-slate-300" };
  }
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [mapProjects, setMapProjects] = useState<MapProject[]>([]);
  const [allProjects, setAllProjects] = useState<RiskProject[]>([]);
  const [readiness, setReadiness] = useState<DataReadiness | null>(null);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertsUpdatedAt, setAlertsUpdatedAt] = useState<Date | null>(null);
  const [alertsRefreshing, setAlertsRefreshing] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] =
    useState<(typeof RISK_LEVELS)[number]>("ALL");

  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [datasetBusy, setDatasetBusy] = useState(false);
  const [datasetMessage, setDatasetMessage] = useState("");

  useEffect(() => {
    loadDashboard();
    loadAlerts();

    // Live monitoring: re-poll alerts every 30s so the feed reflects
    // the current dataset without any human having to refresh or
    // review anything first.
    const interval = setInterval(loadAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError("");

      const [summaryRes, mapRes, analysisRes, readinessRes, insightsRes] =
        await Promise.all([
          fetch(`${API_URL}/risk-summary`),
          fetch(`${API_URL}/map-projects`),
          fetch(`${API_URL}/risk-analysis`),
          fetch(`${API_URL}/data-readiness`),
          fetch(`${API_URL}/insights`),
        ]);

      if (
        !summaryRes.ok ||
        !mapRes.ok ||
        !analysisRes.ok ||
        !readinessRes.ok ||
        !insightsRes.ok
      ) {
        throw new Error(
          `Server returned an error (status ${summaryRes.status}/${mapRes.status}/${analysisRes.status}/${readinessRes.status}/${insightsRes.status})`
        );
      }

      const [summaryData, mapData, analysisData, readinessData, insightsData] =
        await Promise.all([
          summaryRes.json(),
          mapRes.json(),
          analysisRes.json(),
          readinessRes.json(),
          insightsRes.json(),
        ]);

      setSummary(summaryData);
      setMapProjects(Array.isArray(mapData) ? mapData : []);
      setAllProjects(Array.isArray(analysisData) ? analysisData : []);
      setReadiness(readinessData);
      setInsights(insightsData);

      await loadAlerts();
    } catch (err) {
      console.error("Dashboard loading error:", err);

      if (err instanceof TypeError) {
        setError(
          "Cannot connect to the MPLAD-GUARD AI backend. Make sure FastAPI is running on http://127.0.0.1:8000."
        );
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to load dashboard data.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadAlerts() {
    setAlertsRefreshing(true);

    try {
      const response = await fetch(`${API_URL}/alerts`);

      if (!response.ok) return;

      const data = await response.json();

      setAlerts(Array.isArray(data) ? data : []);
      setAlertsUpdatedAt(new Date());
    } catch (err) {
      console.error("Alerts refresh error:", err);
    } finally {
      setAlertsRefreshing(false);
    }
  }

  async function uploadDataset() {
    if (!uploadFile) return;

    setDatasetBusy(true);
    setDatasetMessage("");

    try {
      const formData = new FormData();
      formData.append("projects", uploadFile);

      const response = await fetch(`${API_URL}/dataset/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Dataset upload failed");
      }

      setDatasetMessage(
        `Loaded ${uploadFile.name} — ${data.signals_available}/${data.signals_total} AI signals active.`
      );
      setUploadFile(null);
      await loadDashboard();
    } catch (err) {
      setDatasetMessage(
        err instanceof Error ? err.message : "Unable to upload dataset."
      );
    } finally {
      setDatasetBusy(false);
    }
  }

  async function resetDataset() {
    setDatasetBusy(true);
    setDatasetMessage("");

    try {
      const response = await fetch(`${API_URL}/dataset/reset`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Could not reset to the demo dataset.");
      }

      setDatasetMessage("Reset to the bundled demo dataset.");
      await loadDashboard();
    } catch (err) {
      setDatasetMessage(
        err instanceof Error ? err.message : "Unable to reset dataset."
      );
    } finally {
      setDatasetBusy(false);
    }
  }

  const MAX_ROWS_SHOWN = 200;

  const filteredProjects = useMemo(() => {
    return allProjects.filter((project) => {
      const matchesLevel =
        levelFilter === "ALL" || project.risk_level === levelFilter;

      const query = search.trim().toLowerCase();

      const matchesSearch =
        query === "" ||
        project.project_id.toLowerCase().includes(query) ||
        project.project_name.toLowerCase().includes(query) ||
        project.district.toLowerCase().includes(query) ||
        project.mp_name.toLowerCase().includes(query) ||
        project.contractor.toLowerCase().includes(query);

      return matchesLevel && matchesSearch;
    });
  }, [allProjects, search, levelFilter]);

  const visibleProjects = filteredProjects.slice(0, MAX_ROWS_SHOWN);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="text-3xl font-bold mb-3">MPLAD-GUARD AI</div>
          <p className="text-slate-500">Loading risk intelligence dashboard...</p>
        </div>
      </main>
    );
  }

  if (error || !summary) {
    return (
      <main className="min-h-screen bg-slate-50 text-slate-900 flex items-center justify-center px-6">
        <div className="max-w-lg w-full bg-white border border-red-200 rounded-2xl p-8 text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold">Unable to Load Dashboard</h1>
          <p className="text-red-600 mt-4">
            {error || "Dashboard data unavailable."}
          </p>
          <button
            onClick={() => loadDashboard()}
            className="mt-6 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white/95">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <p className="text-sm text-blue-600 font-semibold">MPLAD-GUARD AI</p>
          <h1 className="text-2xl md:text-3xl font-bold mt-1">
            MPLADS Risk Intelligence Dashboard
          </h1>
          <p className="text-slate-500 mt-2 max-w-3xl">
            Every project below is scored, explained, and monitored
            automatically — no human review is required to generate this
            analysis. Human verification (inside each project) is an optional
            accountability layer on top, not a prerequisite.
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* DATA READINESS + DATASET UPLOAD */}
        <section className="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
          <div className="flex flex-col lg:flex-row justify-between gap-6">
            <div>
              <h2 className="text-xl font-bold">📂 Data Readiness</h2>
              <p className="text-sm text-slate-500 mt-1">
                {readiness?.using_default_dataset
                  ? "Using the bundled demo dataset."
                  : "Using an uploaded dataset."}{" "}
                {readiness && (
                  <span className="text-slate-700 font-semibold">
                    {readiness.signals_available}/{readiness.signals_total} AI
                    signals active
                  </span>
                )}
              </p>

              {readiness && (
                <div className="flex flex-wrap gap-2 mt-4">
                  {Object.entries(readiness.signal_availability).map(
                    ([signal, available]) => (
                      <span
                        key={signal}
                        className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                          available
                            ? "bg-green-50 text-green-700 border-green-200"
                            : "bg-slate-100 text-slate-500 border-slate-300"
                        }`}
                        title={
                          available
                            ? "This signal is active for the current dataset"
                            : "Not enough columns/files supplied for this signal"
                        }
                      >
                        {available ? "✓" : "—"} {SIGNAL_LABELS[signal] || signal}
                      </span>
                    )
                  )}
                </div>
              )}
            </div>

            <div className="lg:min-w-[320px]">
              <p className="text-sm font-medium text-slate-700 mb-2">
                Try your own dataset
              </p>

              <p className="text-xs text-slate-500 mb-3">
                Upload any CSV/XLSX with a project identifier column —
                headers don&apos;t need to match ours, common synonyms are
                auto-detected.
              </p>

              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="text-xs text-slate-500 file:mr-3 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-slate-100 file:text-slate-900 file:text-xs file:font-semibold flex-1"
                />

                <div className="flex gap-2">
                  <button
                    disabled={!uploadFile || datasetBusy}
                    onClick={uploadDataset}
                    className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 font-semibold text-sm whitespace-nowrap"
                  >
                    Analyze
                  </button>

                  {readiness && !readiness.using_default_dataset && (
                    <button
                      disabled={datasetBusy}
                      onClick={resetDataset}
                      className="px-4 py-2 rounded-xl bg-slate-200 hover:bg-slate-300 disabled:opacity-50 font-semibold text-sm whitespace-nowrap"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {datasetMessage && (
                <p className="text-xs text-slate-500 mt-3">{datasetMessage}</p>
              )}
            </div>
          </div>
        </section>

        {/* SUMMARY CARDS */}
        <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          <StatCard label="Total Projects" value={summary.total_projects} />
          <StatCard
            label="Avg Risk Score"
            value={summary.average_risk_score.toFixed(1)}
          />
          <StatCard
            label="Critical"
            value={summary.critical_risk}
            accent="text-red-600"
          />
          <StatCard
            label="High"
            value={summary.high_risk}
            accent="text-orange-600"
          />
          <StatCard
            label="Medium"
            value={summary.medium_risk}
            accent="text-yellow-700"
          />
          <StatCard
            label="Active Alerts"
            value={summary.total_alerts}
            accent="text-blue-600"
          />
        </section>

        {/* PROJECT STATUS */}
        {insights && insights.status_breakdown.length > 0 && (
          <section className="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
            <h2 className="text-xl font-bold flex items-center gap-2">
              📁 Project Status
            </h2>
            <p className="text-sm text-slate-500 mb-5">
              How many projects are completed, still in progress, or running
              late — at a glance
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 mb-5">
              {insights.status_breakdown.map((row) => {
                const meta = statusMeta(row.status);
                return (
                  <div
                    key={row.status}
                    className={`rounded-xl border p-4 ${meta.className}`}
                  >
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <span className="text-lg">{meta.icon}</span>
                      {row.status}
                    </div>
                    <p className="text-3xl font-bold mt-2">{row.count}</p>
                    <p className="text-xs opacity-80 mt-1">
                      {row.percentage}% of all projects
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Proportional status bar for an instant visual read */}
            <div className="h-3 w-full rounded-full overflow-hidden flex bg-slate-100">
              {insights.status_breakdown.map((row) => {
                const barColor =
                  row.status.toLowerCase() === "completed"
                    ? "bg-green-500"
                    : row.status.toLowerCase() === "in progress"
                    ? "bg-blue-500"
                    : row.status.toLowerCase() === "delayed"
                    ? "bg-orange-500"
                    : "bg-slate-400";
                return (
                  <div
                    key={row.status}
                    className={barColor}
                    style={{ width: `${row.percentage}%` }}
                    title={`${row.status}: ${row.count} (${row.percentage}%)`}
                  />
                );
              })}
            </div>
          </section>
        )}

        {/* LIVE ALERTS FEED */}
        <section className="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1">
            <h2 className="text-xl font-bold">🚨 Live Alerts</h2>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              {alertsRefreshing && <span>Refreshing…</span>}
              {alertsUpdatedAt && (
                <span>
                  Last updated: {alertsUpdatedAt.toLocaleTimeString("en-IN")}
                </span>
              )}
              <button
                onClick={() => loadAlerts()}
                className="px-3 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 font-semibold"
              >
                Refresh
              </button>
            </div>
          </div>
          <p className="text-sm text-slate-500 mb-4">
            Generated automatically — a project qualifies for an alert if its
            blended risk score reaches 40+, or if a single high-precision
            signal (financial, document, image, duplicate, geo-spatial, ML,
            or citizen) fires on its own. No human review needed to produce
            this list. Auto-refreshes every 30 seconds.
          </p>

          {alerts.length === 0 ? (
            <div className="border border-dashed border-slate-300 rounded-xl p-6 text-center text-slate-500">
              No active alerts for the current dataset.
            </div>
          ) : (
            <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
              {alerts.map((alert) => (
                <div
                  key={alert.project_id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50 border border-slate-200 rounded-xl p-4"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-bold border ${riskBadgeClass(
                          alert.risk_level
                        )}`}
                      >
                        {alert.alert_type}
                      </span>
                      <p className="font-semibold truncate">
                        {alert.project_name}
                      </p>
                      <span className="text-xs text-slate-500">
                        {alert.project_id} • {alert.district}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {alert.recommended_action}
                    </p>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-sm font-semibold">
                      {Number(alert.overall_risk_score).toFixed(1)}
                    </span>
                    <Link
                      href={`/project/${encodeURIComponent(alert.project_id)}`}
                      className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 font-semibold text-xs whitespace-nowrap"
                    >
                      Investigate →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* PORTFOLIO AI INSIGHTS */}
        {insights && (
          <section className="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
            <h2 className="text-xl font-bold mb-1">📊 Portfolio AI Insights</h2>
            <p className="text-sm text-slate-500 mb-5">
              A complete automatic overview across all {insights.total_projects}{" "}
              projects — computed the moment the dataset loads, independent of
              any human verification.
            </p>

            <div className="grid sm:grid-cols-3 gap-4 mb-6">
              <InsightStat
                label="Flagged Projects (Alerts)"
                value={`${insights.flagged_projects}`}
                sub={`${insights.flagged_percentage}% of portfolio`}
              />
              <InsightStat
                label="Sanctioned Amount at Risk"
                value={formatCurrency(insights.sanctioned_amount_at_risk)}
                sub={`${insights.sanctioned_at_risk_percentage}% of ${formatCurrency(
                  insights.total_sanctioned_amount
                )} total`}
                accent="text-orange-600"
              />
              <InsightStat
                label="Total Sanctioned"
                value={formatCurrency(insights.total_sanctioned_amount)}
                sub={`across ${insights.total_projects} projects`}
              />
            </div>

            {/* REAL-TIME FUND TRACKING */}
            <div className="mb-6">
              <h3 className="font-bold mb-3">💰 Real-Time Fund Tracking</h3>
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <InsightStat
                  label="Released"
                  value={formatCurrency(insights.fund_tracking.total_released)}
                  sub={`${insights.fund_tracking.release_rate_percentage}% of sanctioned`}
                />
                <InsightStat
                  label="Utilized"
                  value={formatCurrency(insights.fund_tracking.total_utilized)}
                  sub={`${insights.fund_tracking.utilization_rate_percentage}% of released`}
                />
                <InsightStat
                  label="Unutilized Funds"
                  value={formatCurrency(insights.fund_tracking.unutilized_funds)}
                  sub="released but not yet spent"
                  accent="text-yellow-700"
                />
                <InsightStat
                  label="Utilization Rate"
                  value={`${insights.fund_tracking.utilization_rate_percentage}%`}
                  sub="utilized ÷ released"
                />
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <BarListCard
                title="AI Signal Frequency"
                description="How often each of the 11 signals fires across the portfolio"
                items={insights.signal_frequency.map((row) => ({
                  label: row.signal,
                  value: row.flagged_projects,
                  sublabel: `${row.percentage}%`,
                }))}
              />

              <BarListCard
                title="Top Districts by Average Risk"
                description="Geographic concentration of AI-flagged risk"
                items={insights.risk_by_district.map((row) => ({
                  label: row.name,
                  value: row.average_risk_score,
                  sublabel: `${row.project_count} projects`,
                }))}
              />

              <BarListCard
                title="Top Contractors by Average Risk"
                description="Accountability concentration — same contractor, repeated risk"
                items={insights.risk_by_contractor.map((row) => ({
                  label: row.name,
                  value: row.average_risk_score,
                  sublabel: `${row.project_count} projects`,
                }))}
              />

              <BarListCard
                title="Top Project Types by Average Risk"
                description="Which categories of work concentrate risk"
                items={insights.risk_by_project_type.map((row) => ({
                  label: row.name,
                  value: row.average_risk_score,
                  sublabel: `${row.project_count} projects`,
                }))}
              />
            </div>

            {/* GEO-SPATIAL ANOMALIES */}
            {insights.geo_overlap_pairs.length > 0 && (
              <div className="mt-6 bg-slate-50 border border-slate-200 rounded-xl p-5">
                <h3 className="font-bold">📍 Geo-Spatial Anomalies</h3>
                <p className="text-xs text-slate-500 mb-4">
                  Project pairs whose sanctioned locations sit within 300 m of
                  each other — shown on the map below with a dashed violet
                  ring
                </p>

                <div className="space-y-2">
                  {insights.geo_overlap_pairs.map((pair, index) => (
                    <div
                      key={index}
                      className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-white border border-slate-200 rounded-lg p-3 text-sm"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          href={`/project/${encodeURIComponent(pair.project_id_1)}`}
                          className="text-blue-600 hover:text-blue-700 font-medium"
                        >
                          {pair.project_name_1}
                        </Link>
                        <span className="text-slate-500">↔</span>
                        <Link
                          href={`/project/${encodeURIComponent(pair.project_id_2)}`}
                          className="text-blue-600 hover:text-blue-700 font-medium"
                        >
                          {pair.project_name_2}
                        </Link>
                      </div>
                      <span className="text-slate-500 text-xs whitespace-nowrap">
                        {Math.round(pair.distance_km * 1000)} m apart
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* MAP */}
        <section className="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-4">
            <div>
              <h2 className="text-xl font-bold mb-1">
                🗺️ Project Risk Map
              </h2>
              <p className="text-sm text-slate-500">
                Bigger, redder markers mean higher AI risk. Click any marker
                for full details.
              </p>
            </div>

            {/* Visual legend -- what each marker color/ring means, at a glance */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5">
              <LegendDot color="#ef4444" label="Critical" />
              <LegendDot color="#f97316" label="High" />
              <LegendDot color="#eab308" label="Medium" />
              <LegendDot color="#22c55e" label="Low" />
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full border-2 border-dashed border-violet-500" />
                Location overlap (&lt;300m)
              </span>
            </div>
          </div>

          <MapView projects={mapProjects} />
        </section>

        {/* PROJECT RISK TABLE */}
        <section className="bg-white border border-slate-200 rounded-2xl p-6 mb-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5">
            <div>
              <h2 className="text-xl font-bold">🔍 Project Risk Explorer</h2>
              <p className="text-sm text-slate-500 mt-1">
                All {allProjects.length} projects, ranked by AI risk score —
                filter by risk level or search
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search project, district, MP, contractor..."
                className="bg-slate-50 border border-slate-300 rounded-xl px-4 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 min-w-[260px]"
              />

              <select
                value={levelFilter}
                onChange={(e) =>
                  setLevelFilter(
                    e.target.value as (typeof RISK_LEVELS)[number]
                  )
                }
                className="bg-slate-50 border border-slate-300 rounded-xl px-4 py-2 text-sm text-slate-900 focus:outline-none focus:border-blue-500"
              >
                {RISK_LEVELS.map((level) => (
                  <option key={level} value={level}>
                    {level === "ALL" ? "All Risk Levels" : level}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {filteredProjects.length === 0 ? (
            <div className="border border-dashed border-slate-300 rounded-xl p-8 text-center">
              <p className="text-slate-500">
                No projects match your filters.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              {filteredProjects.length > MAX_ROWS_SHOWN && (
                <p className="text-xs text-slate-500 mb-3">
                  Showing top {MAX_ROWS_SHOWN} of {filteredProjects.length}{" "}
                  matching projects by risk score. Refine your search or
                  filter to narrow further.
                </p>
              )}

              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-slate-200">
                    <th className="py-3 pr-4">Project</th>
                    <th className="py-3 pr-4">District / MP</th>
                    <th className="py-3 pr-4">Contractor</th>
                    <th className="py-3 pr-4">Risk Score</th>
                    <th className="py-3 pr-4">Level</th>
                    <th className="py-3 pr-4">Priority</th>
                    <th className="py-3 pr-4" />
                  </tr>
                </thead>
                <tbody>
                  {visibleProjects.map((project) => (
                    <tr
                      key={project.project_id}
                      className="border-b border-slate-200 hover:bg-slate-50"
                    >
                      <td className="py-3 pr-4">
                        <p className="font-semibold">{project.project_name}</p>
                        <p className="text-xs text-slate-500">
                          {project.project_id}
                        </p>
                      </td>
                      <td className="py-3 pr-4 text-slate-700">
                        {project.district}
                        <p className="text-xs text-slate-500">
                          {project.mp_name}
                        </p>
                      </td>
                      <td className="py-3 pr-4 text-slate-700">
                        {project.contractor}
                      </td>
                      <td className="py-3 pr-4 font-semibold">
                        {Number(project.overall_risk_score).toFixed(1)}
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`inline-block px-3 py-1 rounded-full text-xs font-bold border ${riskBadgeClass(
                            project.risk_level
                          )}`}
                        >
                          {project.risk_level}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-slate-700">
                        {project.priority}
                      </td>
                      <td className="py-3 pr-4 text-right">
                        <Link
                          href={`/project/${encodeURIComponent(
                            project.project_id
                          )}`}
                          className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold text-slate-900 whitespace-nowrap"
                        >
                          Investigate →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <footer className="text-center text-slate-500 text-sm pb-8">
          MPLAD-GUARD AI • Explainable AI-assisted risk intelligence and
          human verification
        </footer>
      </div>
    </main>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className="w-3 h-3 rounded-full shrink-0"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-3xl font-bold mt-2 ${accent || ""}`}>{value}</p>
    </div>
  );
}

function InsightStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  accent?: string;
}) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${accent || ""}`}>{value}</p>
      <p className="text-xs text-slate-500 mt-1">{sub}</p>
    </div>
  );
}

function BarListCard({
  title,
  description,
  items,
}: {
  title: string;
  description: string;
  items: { label: string; value: number; sublabel: string }[];
}) {
  const maxValue = Math.max(1, ...items.map((item) => item.value));

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-5">
      <h3 className="font-bold">{title}</h3>
      <p className="text-xs text-slate-500 mb-4">{description}</p>

      {items.length === 0 ? (
        <p className="text-sm text-slate-500">Not enough data to rank.</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.label}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-slate-700 font-medium truncate pr-2">
                  {item.label}
                </span>
                <span className="text-slate-500 whitespace-nowrap">
                  {item.value.toFixed(item.value % 1 === 0 ? 0 : 1)} ·{" "}
                  {item.sublabel}
                </span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{
                    width: `${Math.max(4, (item.value / maxValue) * 100)}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
