"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] w-full rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500">
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
};

const RISK_LEVELS = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

function riskBadgeClass(level: string) {
  switch (level) {
    case "CRITICAL":
      return "bg-red-950 text-red-300 border-red-900";
    case "HIGH":
      return "bg-orange-950 text-orange-300 border-orange-900";
    case "MEDIUM":
      return "bg-yellow-950 text-yellow-300 border-yellow-900";
    default:
      return "bg-green-950 text-green-300 border-green-900";
  }
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<RiskSummary | null>(null);
  const [mapProjects, setMapProjects] = useState<MapProject[]>([]);
  const [allProjects, setAllProjects] = useState<RiskProject[]>([]);
  const [readiness, setReadiness] = useState<DataReadiness | null>(null);

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
  }, []);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError("");

      const [summaryRes, mapRes, analysisRes, readinessRes] = await Promise.all([
        fetch(`${API_URL}/risk-summary`),
        fetch(`${API_URL}/map-projects`),
        fetch(`${API_URL}/risk-analysis`),
        fetch(`${API_URL}/data-readiness`),
      ]);

      if (!summaryRes.ok || !mapRes.ok || !analysisRes.ok || !readinessRes.ok) {
        throw new Error(
          `Server returned an error (status ${summaryRes.status}/${mapRes.status}/${analysisRes.status}/${readinessRes.status})`
        );
      }

      const [summaryData, mapData, analysisData, readinessData] = await Promise.all([
        summaryRes.json(),
        mapRes.json(),
        analysisRes.json(),
        readinessRes.json(),
      ]);

      setSummary(summaryData);
      setMapProjects(Array.isArray(mapData) ? mapData : []);
      setAllProjects(Array.isArray(analysisData) ? analysisData : []);
      setReadiness(readinessData);
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
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="text-3xl font-bold mb-3">MPLAD-GUARD AI</div>
          <p className="text-slate-400">Loading risk intelligence dashboard...</p>
        </div>
      </main>
    );
  }

  if (error || !summary) {
    return (
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center px-6">
        <div className="max-w-lg w-full bg-slate-900 border border-red-900 rounded-2xl p-8 text-center">
          <div className="text-4xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold">Unable to Load Dashboard</h1>
          <p className="text-red-400 mt-4">
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
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <p className="text-sm text-blue-400 font-semibold">MPLAD-GUARD AI</p>
          <h1 className="text-2xl md:text-3xl font-bold mt-1">
            MPLADS Risk Intelligence Dashboard
          </h1>
          <p className="text-slate-400 mt-2 max-w-3xl">
            AI-assisted monitoring across sanctioned MPLAD projects, with
            explainable risk signals and human-in-the-loop verification.
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* DATA READINESS + DATASET UPLOAD */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-8">
          <div className="flex flex-col lg:flex-row justify-between gap-6">
            <div>
              <h2 className="text-xl font-bold">Data Readiness</h2>
              <p className="text-sm text-slate-400 mt-1">
                {readiness?.using_default_dataset
                  ? "Using the bundled demo dataset."
                  : "Using an uploaded dataset."}{" "}
                {readiness && (
                  <span className="text-slate-300 font-semibold">
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
                            ? "bg-green-950 text-green-300 border-green-900"
                            : "bg-slate-800 text-slate-500 border-slate-700"
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
              <p className="text-sm font-medium text-slate-300 mb-2">
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
                  className="text-xs text-slate-400 file:mr-3 file:px-3 file:py-2 file:rounded-lg file:border-0 file:bg-slate-800 file:text-white file:text-xs file:font-semibold flex-1"
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
                      className="px-4 py-2 rounded-xl bg-slate-700 hover:bg-slate-600 disabled:opacity-50 font-semibold text-sm whitespace-nowrap"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {datasetMessage && (
                <p className="text-xs text-slate-400 mt-3">{datasetMessage}</p>
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
            accent="text-red-400"
          />
          <StatCard
            label="High"
            value={summary.high_risk}
            accent="text-orange-400"
          />
          <StatCard
            label="Medium"
            value={summary.medium_risk}
            accent="text-yellow-400"
          />
          <StatCard
            label="Active Alerts"
            value={summary.total_alerts}
            accent="text-blue-400"
          />
        </section>

        {/* MAP */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-bold mb-1">
            Geo-Spatial Project Risk Map
          </h2>
          <p className="text-sm text-slate-400 mb-4">
            Marker size and color reflect overall AI risk level. Click a
            marker for details.
          </p>
          <MapView projects={mapProjects} />
        </section>

        {/* PROJECT RISK TABLE */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-8">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5">
            <div>
              <h2 className="text-xl font-bold">Project Risk Explorer</h2>
              <p className="text-sm text-slate-400 mt-1">
                All {allProjects.length} projects, ranked by AI risk score —
                filter by risk level or search
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search project, district, MP, contractor..."
                className="bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 min-w-[260px]"
              />

              <select
                value={levelFilter}
                onChange={(e) =>
                  setLevelFilter(
                    e.target.value as (typeof RISK_LEVELS)[number]
                  )
                }
                className="bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
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
            <div className="border border-dashed border-slate-700 rounded-xl p-8 text-center">
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
                  <tr className="text-left text-slate-400 border-b border-slate-800">
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
                      className="border-b border-slate-800/60 hover:bg-slate-800/30"
                    >
                      <td className="py-3 pr-4">
                        <p className="font-semibold">{project.project_name}</p>
                        <p className="text-xs text-slate-500">
                          {project.project_id}
                        </p>
                      </td>
                      <td className="py-3 pr-4 text-slate-300">
                        {project.district}
                        <p className="text-xs text-slate-500">
                          {project.mp_name}
                        </p>
                      </td>
                      <td className="py-3 pr-4 text-slate-300">
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
                      <td className="py-3 pr-4 text-slate-300">
                        {project.priority}
                      </td>
                      <td className="py-3 pr-4 text-right">
                        <Link
                          href={`/project/${encodeURIComponent(
                            project.project_id
                          )}`}
                          className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold text-white whitespace-nowrap"
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

        <footer className="text-center text-slate-600 text-sm pb-8">
          MPLAD-GUARD AI • Explainable AI-assisted risk intelligence and
          human verification
        </footer>
      </div>
    </main>
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
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`text-3xl font-bold mt-2 ${accent || ""}`}>{value}</p>
    </div>
  );
}
