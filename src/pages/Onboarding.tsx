import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, SystemInfo, ModelInfo } from "../api/client";
import ProgressBar from "../components/ProgressBar";
import StatusBadge from "../components/StatusBadge";
import { ONBOARD_KEY } from "../constants";

const STEPS = ["Welcome", "Hardware", "Models", "YouTube"];

export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [sys, setSys] = useState<SystemInfo | null>(null);
  const [sysErr, setSysErr] = useState("");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [dlProg, setDlProg] = useState(0);
  const [dlMsg, setDlMsg] = useState("");
  const [yt, setYt] = useState<{
    status: string;
    channel_name: string | null;
    error: string | null;
  } | null>(null);

  useEffect(() => {
    if (step === 1) {
      api.system().then(setSys).catch((e) => setSysErr(String(e.message || e)));
    }
    if (step === 2) {
      api.listModels().then((r) => setModels(r.models)).catch(() => {});
    }
    if (step === 3) {
      api
        .youtubeStatus()
        .then(setYt)
        .catch(() =>
          setYt({ status: "error", channel_name: null, error: "Sidecar offline" })
        );
    }
  }, [step]);

  async function runDownloads() {
    const list = await api.listModels();
    setModels(list.models);
    const targets = list.models.filter(
      (m) => m.id === "wan2.1-1.3b" || m.id === "kokoro-tts"
    );
    for (const m of targets) {
      if (m.installed) continue;
      setDlMsg(`Downloading ${m.name}…`);
      await api.downloadModel(m.id, true);
      await new Promise<void>((resolve) => {
        const es = new EventSource(`${api.base}/models/download/${m.id}/events`);
        es.onmessage = (ev) => {
          const d = JSON.parse(ev.data);
          setDlProg(d.progress || 0);
          setDlMsg(d.message || "");
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
    }
    const refreshed = await api.listModels();
    setModels(refreshed.models);
    setDlMsg("Models ready (stub/mock when GPU weights aren’t present).");
    setDlProg(1);
  }

  function finish() {
    localStorage.setItem(ONBOARD_KEY, "1");
    nav("/");
  }

  return (
    <div style={{ maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <div className="brand" style={{ marginBottom: "1rem" }}>
        <div className="brand-mark" />
        AutoReel Studio
      </div>
      <div className="steps">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`step${i === step ? " on" : ""}${i < step ? " done" : ""}`}
          >
            {i + 1}. {s}
          </div>
        ))}
      </div>

      {step === 0 && (
        <div className="card">
          <h2 className="page-title">Welcome</h2>
          <p className="page-sub">
            AutoReel Studio turns a topic into a faceless explainer video: script → Wan 2.1
            B-roll → voice → captions → optional YouTube upload.
          </p>
          <ul className="muted">
            <li>Models download into app data (no terminal required)</li>
            <li>Default: Wan 2.1 T2V 1.3B — 14B optional</li>
            <li>Mock mode keeps the rest of the app working without GPU weights</li>
          </ul>
          <button onClick={() => setStep(1)}>Get started</button>
        </div>
      )}

      {step === 1 && (
        <div className="card">
          <h2 className="page-title">Hardware check</h2>
          {sysErr && (
            <p className="err-text">
              Cannot reach sidecar: {sysErr}. Start it with <code>npm run sidecar</code>.
            </p>
          )}
          {sys && (
            <div className="grid grid-2">
              <div>
                <div className="stat-label">OS</div>
                <div className="stat" style={{ fontSize: "1.1rem" }}>
                  {sys.os} ({sys.arch})
                </div>
              </div>
              <div>
                <div className="stat-label">RAM</div>
                <div className="stat" style={{ fontSize: "1.1rem" }}>
                  {sys.ram_gb} GB
                </div>
              </div>
              <div>
                <div className="stat-label">GPU</div>
                <div className="stat" style={{ fontSize: "1.1rem" }}>
                  {sys.gpu.name || sys.gpu.backend}
                </div>
              </div>
              <div>
                <div className="stat-label">Disk free</div>
                <div className="stat" style={{ fontSize: "1.1rem" }}>
                  {sys.disk_free_gb} GB
                </div>
              </div>
              <div>
                <div className="stat-label">FFmpeg</div>
                <div>{sys.ffmpeg}</div>
              </div>
              <div>
                <div className="stat-label">Recommendation</div>
                <div>
                  {sys.ready_for_wan
                    ? "✅ Enough RAM for Wan path"
                    : "⚠️ 16GB RAM recommended"}
                </div>
              </div>
            </div>
          )}
          <div className="row" style={{ marginTop: "1rem" }}>
            <button className="ghost" onClick={() => setStep(0)}>
              Back
            </button>
            <button onClick={() => setStep(2)}>Continue</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="card">
          <h2 className="page-title">Download models</h2>
          <p className="muted">
            Wan 1.3B is multi-GB. Stubs are installed here so mock end-to-end jobs work.
          </p>
          <ProgressBar value={dlProg} />
          <p className="muted">{dlMsg || "Idle"}</p>
          <ul>
            {models.map((m) => (
              <li key={m.id}>
                {m.name} (~{m.size_gb} GB) —{" "}
                {m.installed ? (
                  <StatusBadge status="installed" />
                ) : (
                  <StatusBadge status="missing" />
                )}
              </li>
            ))}
          </ul>
          <div className="row">
            <button className="ghost" onClick={() => setStep(1)}>
              Back
            </button>
            <button onClick={runDownloads}>Download required</button>
            <button onClick={() => setStep(3)}>Skip / Continue</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="card">
          <h2 className="page-title">Connect YouTube</h2>
          <p className="muted">
            Optional. Needs YOUTUBE_CLIENT_ID / SECRET in .env (installed-app loopback OAuth).
          </p>
          {yt && (
            <p>
              Status: <StatusBadge status={yt.status} />{" "}
              {yt.channel_name && <strong>{yt.channel_name}</strong>}
              {yt.error && <span className="err-text"> — {yt.error}</span>}
            </p>
          )}
          <div className="row">
            <button className="ghost" onClick={() => setStep(2)}>
              Back
            </button>
            <button
              onClick={async () => {
                try {
                  setYt(await api.youtubeConnect());
                } catch (e: unknown) {
                  setYt({
                    status: "error",
                    channel_name: null,
                    error: String(e),
                  });
                }
              }}
            >
              Connect
            </button>
            <button onClick={finish}>Finish setup</button>
          </div>
        </div>
      )}
    </div>
  );
}
