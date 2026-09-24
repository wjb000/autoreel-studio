import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Job, SystemInfo } from "../api/client";
import ProgressBar from "../components/ProgressBar";
import StatusBadge from "../components/StatusBadge";

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sys, setSys] = useState<SystemInfo | null>(null);
  const [err, setErr] = useState("");

  async function refresh() {
    try {
      const [j, s] = await Promise.all([api.listJobs(), api.system()]);
      setJobs(j.jobs);
      setSys(s);
      setErr("");
    } catch (e: unknown) {
      setErr(String((e as Error).message || e));
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, []);

  const queue = jobs.filter((j) => j.status === "queued" || j.status === "running");

  return (
    <div>
      <div className="row">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-sub">Create animated shorts or explainers, watch the queue, publish when ready.</p>
        </div>
        <div className="spacer" />
        <Link to="/create">
          <button>Create content</button>
        </Link>
      </div>

      {err && (
        <div className="card err-text">
          Sidecar unreachable: {err}. Run <code>npm run sidecar</code> or <code>scripts/dev.sh</code>.
        </div>
      )}

      {sys && (
        <div className="grid grid-3">
          <div className="card">
            <div className="stat-label">System</div>
            <div className="stat" style={{ fontSize: "1.1rem" }}>
              {sys.os} · {sys.arch}
            </div>
            <div className="muted">{sys.ram_available_gb} GB RAM free · GPU: {sys.gpu.backend}</div>
          </div>
          <div className="card">
            <div className="stat-label">Queue</div>
            <div className="stat">{queue.length}</div>
            <div className="muted">active / queued jobs</div>
          </div>
          <div className="card">
            <div className="stat-label">Mode</div>
            <div className="stat" style={{ fontSize: "1.1rem" }}>
              {sys.mock_wan ? "Mock Wan" : "Real Wan"}
            </div>
            <div className="muted">{sys.app_data}</div>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Recent jobs</h3>
        {jobs.length === 0 ? (
          <p className="muted">No jobs yet. Create your first video.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Topic</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Output</th>
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 12).map((j) => (
                <tr key={j.id}>
                  <td>
                    <strong>{j.topic}</strong>
                    <div className="muted" style={{ fontSize: "0.75rem" }}>
                      {j.id} · {j.mode || "explainer"} · {j.niche}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={j.status} />
                    <div className="muted" style={{ fontSize: "0.75rem" }}>
                      {j.stage}: {j.message}
                    </div>
                  </td>
                  <td style={{ minWidth: 120 }}>
                    <ProgressBar value={j.progress} />
                  </td>
                  <td className="muted" style={{ fontSize: "0.8rem" }}>
                    {j.output?.video || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
