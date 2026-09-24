import { useEffect, useState } from "react";
import { api, ModelInfo } from "../api/client";
import ProgressBar from "../components/ProgressBar";
import StatusBadge from "../components/StatusBadge";

export default function Models() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [prog, setProg] = useState(0);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function refresh() {
    try {
      const r = await api.listModels();
      setModels(r.models);
      setErr("");
    } catch (e: unknown) {
      setErr(String((e as Error).message || e));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function download(id: string) {
    setActive(id);
    setProg(0);
    setMsg("Starting…");
    try {
      await api.downloadModel(id, true);
      await new Promise<void>((resolve) => {
        const es = new EventSource(`${api.base}/models/download/${id}/events`);
        es.onmessage = (ev) => {
          const d = JSON.parse(ev.data);
          setProg(d.progress || 0);
          setMsg(d.message || "");
          if (d.status === "ready" || d.status === "error") {
            es.close();
            resolve();
          }
        };
        es.onerror = () => {
          es.close();
          resolve();
        };
      });
      await refresh();
    } catch (e: unknown) {
      setMsg(String((e as Error).message || e));
    } finally {
      setActive(null);
    }
  }

  return (
    <div>
      <h1 className="page-title">Models</h1>
      <p className="page-sub">
        Download Wan 2.1, Kokoro TTS, and optional script LLM into app data. Wan 2.1 is Apache 2.0.
      </p>
      {err && <div className="card err-text">{err}</div>}
      {active && (
        <div className="card">
          <strong>Downloading {active}</strong>
          <ProgressBar value={prog} />
          <p className="muted">{msg}</p>
        </div>
      )}
      <div className="grid">
        {models.map((m) => (
          <div className="card" key={m.id}>
            <div className="row">
              <h3 style={{ margin: 0 }}>{m.name}</h3>
              <div className="spacer" />
              {m.installed ? <StatusBadge status="installed" /> : <StatusBadge status="missing" />}
              {m.required && <StatusBadge status="required" />}
            </div>
            <p className="muted">{m.description}</p>
            <div className="row muted" style={{ fontSize: "0.85rem" }}>
              <span>~{m.size_gb} GB</span>
              <span>on disk: {m.size_on_disk_gb} GB</span>
              <span>{m.license}</span>
            </div>
            <p className="muted" style={{ fontSize: "0.75rem" }}>
              {m.path}
            </p>
            <button disabled={!!active} onClick={() => download(m.id)}>
              {m.installed ? "Re-download / update" : "Download"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
