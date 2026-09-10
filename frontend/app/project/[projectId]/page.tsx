"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Project = {
  project_id: string;
  project_name: string;
  state: string;
  district: string;
  mp_name: string;
  project_type: string;
  contractor: string;
  agency: string;
  status: string;

  sanctioned_amount: number;
  released_amount: number;
  utilized_amount: number;
  completion_percentage: number;

  overall_risk_score: number;
  risk_level: string;
  risk_signal_count: number;
  priority: string;

  financial_risk_score: number;
  delay_risk_score: number;
  progress_risk_score: number;
  contractor_risk_score: number;
  document_risk_score: number;
  image_risk_score: number;
  inspection_risk_score: number;
  ml_anomaly_score: number;
  duplicate_risk_score: number;

  recommended_action: string;
  risk_reasons: string[];
};

type Verification = {
  project_id: string;
  decision: string;
  remarks: string;
  verified_by: string;
  verification_date: string;
};

export default function ProjectInvestigationPage() {
  const params = useParams();

  const projectId = Array.isArray(params.projectId)
    ? params.projectId[0]
    : params.projectId;

  const [project, setProject] = useState<Project | null>(null);
  const [history, setHistory] = useState<Verification[]>([]);

  const [loading, setLoading] = useState(true);
  const [verificationLoading, setVerificationLoading] = useState(false);

  const [error, setError] = useState("");
  const [remarks, setRemarks] = useState("");

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"success" | "error" | "">(
    ""
  );

  async function loadProject() {
    try {
      setLoading(true);
      setError("");

      const url = `${API_URL}/project/${encodeURIComponent(
        String(projectId)
      )}`;

      console.log("Loading project:", url);

      const response = await fetch(url);

      console.log("Project API status:", response.status);

      if (!response.ok) {
        let detail = `Server returned ${response.status}`;

        try {
          const data = await response.json();

          if (data?.detail) {
            detail = data.detail;
          }
        } catch {
          // Ignore invalid JSON
        }

        throw new Error(detail);
      }

      const data = await response.json();

      console.log("Project data:", data);

      setProject(data);
    } catch (err) {
      console.error("Project loading error:", err);

      if (err instanceof TypeError) {
        setError(
          "Cannot connect to the MPLAD-GUARD AI backend. Make sure FastAPI is running on port 8000."
        );
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to load project.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadVerificationHistory() {
    if (!projectId) return;

    try {
      const response = await fetch(
        `${API_URL}/project/${encodeURIComponent(
          String(projectId)
        )}/verification-history`
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setHistory(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Verification history error:", error);
    }
  }

  useEffect(() => {
    // Re-fetch whenever the route param changes (client-side navigation
    // between /project/A and /project/B reuses this component instance).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProject();
    loadVerificationHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function submitVerification(decision: string) {
    if (!projectId) return;

    setVerificationLoading(true);
    setMessage("");
    setMessageType("");

    try {
      const response = await fetch(
        `${API_URL}/project/${encodeURIComponent(
          String(projectId)
        )}/verify`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            decision,
            remarks,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Verification failed");
      }

      setMessage(
        `Project ${decision
          .toLowerCase()
          .replace("_", " ")} successfully recorded.`
      );

      setMessageType("success");
      setRemarks("");

      await loadVerificationHistory();
    } catch (error) {
      console.error(error);

      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to save verification decision."
      );

      setMessageType("error");
    } finally {
      setVerificationLoading(false);
    }
  }

  if (!projectId) {
    return (
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center px-6">
        <div className="max-w-lg w-full bg-slate-900 border border-red-900 rounded-2xl p-8 text-center">
          <div className="text-4xl mb-4">⚠️</div>

          <h1 className="text-2xl font-bold">
            Unable to Load Project
          </h1>

          <p className="text-red-400 mt-4">
            Project ID is missing.
          </p>

          <Link
            href="/"
            className="inline-block mt-6 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold"
          >
            Back to Dashboard
          </Link>
        </div>
      </main>
    );
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center">
        <div className="text-center">
          <div className="text-3xl font-bold mb-3">
            MPLAD-GUARD AI
          </div>

          <p className="text-slate-400">
            Loading project intelligence...
          </p>

          <p className="text-xs text-slate-600 mt-3">
            Project: {projectId}
          </p>
        </div>
      </main>
    );
  }

  if (error || !project) {
    return (
      <main className="min-h-screen bg-slate-950 text-white flex items-center justify-center px-6">
        <div className="max-w-lg w-full bg-slate-900 border border-red-900 rounded-2xl p-8 text-center">
          <div className="text-4xl mb-4">⚠️</div>

          <h1 className="text-2xl font-bold">
            Unable to Load Project
          </h1>

          <p className="text-red-400 mt-4">
            {error || "Project data unavailable."}
          </p>

          <p className="text-slate-500 text-sm mt-4">
            Project ID: {projectId}
          </p>

          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 font-semibold"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  const riskColor =
    project.risk_level === "CRITICAL"
      ? "text-red-400"
      : project.risk_level === "HIGH"
      ? "text-orange-400"
      : project.risk_level === "MEDIUM"
      ? "text-yellow-400"
      : "text-green-400";

  function formatDate(date: string) {
    if (!date) return "-";

    const parsed = new Date(date);

    if (Number.isNaN(parsed.getTime())) {
      return date;
    }

    return parsed.toLocaleString("en-IN");
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-slate-800 bg-slate-950/95">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <Link
                href="/"
                className="text-sm text-blue-400 font-semibold hover:text-blue-300"
              >
                ← MPLAD-GUARD AI
              </Link>

              <h1 className="text-2xl md:text-3xl font-bold mt-1">
                Project Investigation
              </h1>
            </div>

            <div className="text-right">
              <p className="text-sm text-slate-400">
                Project ID
              </p>

              <p className="font-bold text-lg">
                {project.project_id}
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* PROJECT OVERVIEW */}

        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
          <div className="flex flex-col lg:flex-row justify-between gap-6">
            <div>
              <p className="text-sm text-blue-400 mb-2">
                PROJECT
              </p>

              <h2 className="text-2xl font-bold">
                {project.project_name}
              </h2>

              <p className="text-slate-400 mt-3">
                {project.district}, {project.state}
              </p>

              <div className="flex flex-wrap gap-3 mt-4">
                <span className="px-3 py-1 rounded-full bg-slate-800 text-sm">
                  {project.project_type}
                </span>

                <span className="px-3 py-1 rounded-full bg-slate-800 text-sm">
                  {project.status}
                </span>

                <span className="px-3 py-1 rounded-full bg-slate-800 text-sm">
                  Contractor: {project.contractor}
                </span>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 min-w-[240px]">
              <p className="text-sm text-slate-400">
                Overall AI Risk Score
              </p>

              <div className="flex items-end gap-2 mt-2">
                <span className={`text-5xl font-bold ${riskColor}`}>
                  {Number(project.overall_risk_score).toFixed(1)}
                </span>

                <span className="text-slate-500 mb-2">
                  /100
                </span>
              </div>

              <p className={`font-bold mt-2 ${riskColor}`}>
                {project.risk_level}
              </p>

              <p className="text-sm text-slate-500 mt-1">
                {project.risk_signal_count} risk signals detected
              </p>
            </div>
          </div>
        </section>

        {/* RISK ANALYSIS */}

        <section className="grid lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-xl font-bold mb-6">
              AI Risk Breakdown
            </h2>

            <RiskBar
              label="Financial Risk"
              value={project.financial_risk_score}
            />

            <RiskBar
              label="Delay Risk"
              value={project.delay_risk_score}
            />

            <RiskBar
              label="Progress Risk"
              value={project.progress_risk_score}
            />

            <RiskBar
              label="Contractor Risk"
              value={project.contractor_risk_score}
            />

            <RiskBar
              label="Document Risk"
              value={project.document_risk_score}
            />

            <RiskBar
              label="Image Risk"
              value={project.image_risk_score}
            />

            <RiskBar
              label="Inspection Risk"
              value={project.inspection_risk_score}
            />

            <RiskBar
              label="ML Anomaly Score (Isolation Forest)"
              value={project.ml_anomaly_score}
            />

            <RiskBar
              label="Duplicate / Re-registered Project Risk"
              value={project.duplicate_risk_score}
            />
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-xl font-bold mb-6">
              Project Information
            </h2>

            <div className="space-y-4">
              <InfoRow
                label="MP Name"
                value={project.mp_name}
              />

              <InfoRow
                label="Agency"
                value={project.agency}
              />

              <InfoRow
                label="Contractor"
                value={project.contractor}
              />

              <InfoRow
                label="Sanctioned Amount"
                value={`₹${Number(
                  project.sanctioned_amount
                ).toLocaleString("en-IN")}`}
              />

              <InfoRow
                label="Released Amount"
                value={`₹${Number(
                  project.released_amount
                ).toLocaleString("en-IN")}`}
              />

              <InfoRow
                label="Utilized Amount"
                value={`₹${Number(
                  project.utilized_amount
                ).toLocaleString("en-IN")}`}
              />

              <InfoRow
                label="Physical Completion"
                value={`${Number(
                  project.completion_percentage
                ).toFixed(1)}%`}
              />

              <InfoRow
                label="Priority"
                value={project.priority}
              />
            </div>
          </div>
        </section>

        {/* WHY FLAGGED */}

        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-bold">
            Why Was This Project Flagged?
          </h2>

          <p className="text-sm text-slate-400 mt-1">
            Explainable AI evidence behind the risk score
          </p>

          <div className="mt-5 space-y-3">
            {project.risk_reasons &&
            project.risk_reasons.length > 0 ? (
              project.risk_reasons.map(
                (reason, index) => (
                  <div
                    key={index}
                    className="flex gap-3 items-start bg-slate-950 border border-slate-800 rounded-xl p-4"
                  >
                    <span className="text-orange-400 text-lg">
                      ⚠
                    </span>

                    <p className="text-slate-300">
                      {reason}
                    </p>
                  </div>
                )
              )
            ) : (
              <p className="text-slate-400">
                No significant anomaly signals detected.
              </p>
            )}
          </div>
        </section>

        {/* RECOMMENDED ACTION */}

        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
          <h2 className="text-xl font-bold">
            AI Recommended Action
          </h2>

          <div className="mt-4 bg-blue-950/30 border border-blue-900/50 rounded-xl p-5">
            <p className="text-blue-300">
              {project.recommended_action}
            </p>
          </div>
        </section>

        {/* HUMAN VERIFICATION */}

        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
          <div className="flex flex-col md:flex-row justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold">
                Human Verification
              </h2>

              <p className="text-sm text-slate-400 mt-1">
                AI provides risk intelligence. Final action
                remains with the authorized human officer.
              </p>
            </div>

            <div className="text-sm text-slate-500">
              {history.length} previous decision
              {history.length === 1 ? "" : "s"}
            </div>
          </div>

          <div className="mt-6">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Verification Remarks
            </label>

            <textarea
              value={remarks}
              onChange={(e) =>
                setRemarks(e.target.value)
              }
              placeholder="Enter verification remarks..."
              rows={4}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-5">
            <button
              disabled={verificationLoading}
              onClick={() =>
                submitVerification("VERIFIED")
              }
              className="px-4 py-3 rounded-xl bg-green-600 hover:bg-green-500 disabled:opacity-50 font-semibold transition"
            >
              ✓ Verify
            </button>

            <button
              disabled={verificationLoading}
              onClick={() =>
                submitVerification("DISMISSED")
              }
              className="px-4 py-3 rounded-xl bg-slate-700 hover:bg-slate-600 disabled:opacity-50 font-semibold transition"
            >
              ✕ Dismiss
            </button>

            <button
              disabled={verificationLoading}
              onClick={() =>
                submitVerification("FIELD_INSPECTION")
              }
              className="px-4 py-3 rounded-xl bg-orange-600 hover:bg-orange-500 disabled:opacity-50 font-semibold transition"
            >
              ⚑ Field Inspection
            </button>

            <button
              disabled={verificationLoading}
              onClick={() =>
                submitVerification("ESCALATED")
              }
              className="px-4 py-3 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 font-semibold transition"
            >
              ↑ Escalate
            </button>
          </div>

          {message && (
            <div
              className={`mt-5 rounded-xl p-4 border ${
                messageType === "success"
                  ? "bg-green-950/30 border-green-800 text-green-300"
                  : "bg-red-950/30 border-red-800 text-red-300"
              }`}
            >
              {message}
            </div>
          )}
        </section>

        {/* VERIFICATION HISTORY */}

        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-bold">
            Verification History
          </h2>

          <p className="text-sm text-slate-400 mt-1">
            Previous human decisions recorded for this project
          </p>

          {history.length === 0 ? (
            <div className="mt-5 border border-dashed border-slate-700 rounded-xl p-8 text-center">
              <p className="text-slate-500">
                No human verification has been recorded yet.
              </p>
            </div>
          ) : (
            <div className="mt-5 space-y-3">
              {[...history]
                .reverse()
                .map((item, index) => (
                  <div
                    key={index}
                    className="bg-slate-950 border border-slate-800 rounded-xl p-4"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-xs font-bold w-fit ${
                          item.decision === "VERIFIED"
                            ? "bg-green-950 text-green-300"
                            : item.decision === "DISMISSED"
                            ? "bg-slate-800 text-slate-300"
                            : item.decision ===
                              "FIELD_INSPECTION"
                            ? "bg-orange-950 text-orange-300"
                            : "bg-red-950 text-red-300"
                        }`}
                      >
                        {item.decision}
                      </span>

                      <p className="text-xs text-slate-500">
                        {formatDate(
                          item.verification_date
                        )}
                      </p>
                    </div>

                    <p className="text-slate-300 mt-3">
                      {item.remarks ||
                        "No remarks provided."}
                    </p>

                    <p className="text-xs text-slate-500 mt-2">
                      Verified by:{" "}
                      {item.verified_by}
                    </p>
                  </div>
                ))}
            </div>
          )}
        </section>

        <footer className="text-center text-slate-600 text-sm pb-8">
          MPLAD-GUARD AI • Explainable AI-assisted
          risk intelligence and human verification
        </footer>
      </div>
    </main>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-800 pb-3">
      <span className="text-slate-500">
        {label}
      </span>

      <span className="text-right font-medium text-slate-200">
        {value || "-"}
      </span>
    </div>
  );
}

function RiskBar({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const score = Number(value) || 0;

  return (
    <div className="mb-5">
      <div className="flex justify-between mb-2">
        <span className="text-sm text-slate-300">
          {label}
        </span>

        <span className="text-sm font-semibold">
          {score.toFixed(1)}
        </span>
      </div>

      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full"
          style={{
            width: `${Math.min(score, 100)}%`,
          }}
        />
      </div>
    </div>
  );
}