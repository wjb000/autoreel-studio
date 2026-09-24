import { useEffect, useState } from "react";
import { api, Job } from "../api/client";
import ProgressBar from "../components/ProgressBar";
import StatusBadge from "../components/StatusBadge";

type ContentMode = "animated_short" | "explainer";

const MODES: { id: ContentMode; title: string; blurb: string }[] = [
  {
    id: "animated_short",
    title: "Animated short film",
    blurb: "Story beats → Wan clips → VO / captions → film",
  },
  {
    id: "explainer",
    title: "Explainer / facts",
    blurb: "Faceless punchy facts for short-form monetization",
  },
];

export default function Create() {
  const [mode, setMode] = useState<ContentMode>("animated_short");
  const [topic, setTopic] = useState("lost star map");
  const [niche, setNiche] = useState("cinematic animation");
  const [duration, setDuration] = useState("short");
  const [mock, setMock] = useState(true);
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        if (s.default_niche) setNiche(s.default_niche);
        if (s.default_duration) setDuration(s.default_duration);
        if (s.default_mode === "explainer" || s.default_mode === "animated_short") {
          setMode(s.default_mode);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    // Sensible defaults when switching modes
    if (mode === "animated_short") {
      setNiche((n) => (n === "space facts" || n === "interesting facts" ? "cinematic animation" : n));
      setTopic((t) => (t === "black holes" ? "lost star map" : t));
    } else {
      setNiche((n) => (n === "cinematic animation" ? "space facts" : n));
      setTopic((t) => (t === "lost star map" ? "black holes" : t));
    }
  }, [mode]);

  async function generate() {
    setBusy(true);
    setError("");
    setLogs([]);
    try {
      const created = await api.createJob({
        topic,
        niche,
        duration,
        mock,
        mode,
        privacy: "private",
      });
      setJob(created);
      const es = new EventSource(`${api.base}/jobs/${created.id}/events`);
      es.onmessage = (ev) => {
        const d = JSON.parse(ev.data);
        setLogs((prev) => [
          ...prev,
          `[${d.stage}] ${Math.round((d.progress || 0) * 100)}% ${d.message}`,
        ]);
        setJob((prev) =>
          prev
            ? {
                ...prev,
                stage: d.stage,
                progress: d.progress,
                message: d.message,
                status:
                  d.stage === "done" ? "completed" : d.stage === "error" ? "failed" : "running",
                output: d.output || prev.output,
              }
            : prev
        );
        if (d.stage === "done" || d.stage === "error") {
          es.close();
          setBusy(false);
          if (d.stage === "done") {
            api.getJob(created.id).then(setJob).catch(() => {});
          }
        }
      };
      es.onerror = () => {
        es.close();
        setBusy(false);
      };
    } catch (e: unknown) {
      setError(String((e as Error).message || e));
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Create</h1>
      <p className="page-sub">
        Pick a content mode, then generate: beats → Wan clips → voice + captions → assemble.
      </p>

      <div className="mode-grid">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={`mode-card${mode === m.id ? " selected" : ""}`}
            onClick={() => setMode(m.id)}
          >
            <strong>{m.title}</strong>
            <span className="muted">{m.blurb}</span>
          </button>
        ))}
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="field">
            <label>{mode === "animated_short" ? "Story premise / topic" : "Topic"}</label>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder={
                mode === "animated_short" ? "e.g. clockwork fox finds a key" : "e.g. octopus intelligence"
              }
            />
          </div>
          <div className="field">
            <label>{mode === "animated_short" ? "Visual style" : "Niche"}</label>
            <input value={niche} onChange={(e) => setNiche(e.target.value)} />
          </div>
          <div className="field">
            <label>Duration</label>
            <select value={duration} onChange={(e) => setDuration(e.target.value)}>
              <option value="short">Short (~30–45s)</option>
              <option value="medium">Medium (~60–90s)</option>
              <option value="long">Long (~2–3 min)</option>
            </select>
          </div>
          <div className="field row">
            <label style={{ margin: 0 }}>
              <input type="checkbox" checked={mock} onChange={(e) => setMock(e.target.checked)} />{" "}
              Mock Wan (placeholder motion clips)
            </label>
          </div>
          {error && <p className="err-text">{error}</p>}
          <button onClick={generate} disabled={busy || topic.trim().length < 2}>
            {busy ? "Generating…" : mode === "animated_short" ? "Generate short film" : "Generate explainer"}
          </button>
        </div>

        <div className="card">
          <h3>Live progress</h3>
          {job ? (
            <>
              <div className="row">
                <StatusBadge status={job.status} />
                <span className="muted">
                  {job.mode || mode} · {job.stage}
                </span>
              </div>
              <ProgressBar value={job.progress} />
              <p>{job.message}</p>
              {job.output?.video && (
                <p>
                  <strong>Output:</strong> <code>{job.output.video}</code>
                  <br />
                  <strong>Title:</strong> {job.output.title}
                </p>
              )}
              <div className="log">
                {logs.map((l, i) => (
                  <div key={i}>{l}</div>
                ))}
              </div>
            </>
          ) : (
            <p className="muted">Hit Generate to start a job. Progress streams via SSE.</p>
          )}
        </div>
      </div>
    </div>
  );
}
