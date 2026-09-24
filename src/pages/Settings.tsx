import { useEffect, useState } from "react";
import { api, AppSettings } from "../api/client";

export default function SettingsPage() {
  const [s, setS] = useState<AppSettings | null>(null);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .getSettings()
      .then(setS)
      .catch((e) => setErr(String(e.message || e)));
  }, []);

  if (!s && !err) return <p className="muted">Loading…</p>;

  return (
    <div>
      <h1 className="page-title">Settings</h1>
      <p className="page-sub">Defaults, paths, and optional API keys.</p>
      {err && <div className="card err-text">{err}</div>}
      {s && (
        <div className="card" style={{ maxWidth: 560 }}>
          <div className="field">
            <label>Default niche</label>
            <input
              value={s.default_niche}
              onChange={(e) => setS({ ...s, default_niche: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Default voice</label>
            <input
              value={s.default_voice}
              onChange={(e) => setS({ ...s, default_voice: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Default duration</label>
            <select
              value={s.default_duration}
              onChange={(e) => setS({ ...s, default_duration: e.target.value })}
            >
              <option value="short">short</option>
              <option value="medium">medium</option>
              <option value="long">long</option>
            </select>
          </div>
          <div className="field">
            <label>Default upload privacy</label>
            <select
              value={s.default_privacy}
              onChange={(e) => setS({ ...s, default_privacy: e.target.value })}
            >
              <option value="private">private</option>
              <option value="unlisted">unlisted</option>
              <option value="public">public</option>
            </select>
          </div>
          <div className="field">
            <label>Output path</label>
            <input
              value={s.output_path}
              onChange={(e) => setS({ ...s, output_path: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Pexels API key (optional stock fallback)</label>
            <input
              type="password"
              value={s.pexels_api_key}
              onChange={(e) => setS({ ...s, pexels_api_key: e.target.value })}
              placeholder="pxl_…"
            />
          </div>
          <div className="field row">
            <label style={{ margin: 0 }}>
              <input
                type="checkbox"
                checked={s.auto_upload}
                onChange={(e) => setS({ ...s, auto_upload: e.target.checked })}
              />{" "}
              Auto-upload when job completes
            </label>
          </div>
          <div className="row">
            <button
              onClick={async () => {
                const next = await api.saveSettings(s);
                setS(next);
                setSaved(true);
                setTimeout(() => setSaved(false), 2000);
              }}
            >
              Save
            </button>
            {saved && <span className="muted">Saved.</span>}
          </div>
          <p className="muted" style={{ marginTop: "1.5rem", fontSize: "0.85rem" }}>
            YouTube OAuth client ID/secret live in <code>.env</code> (see{" "}
            <code>.env.example</code>). Never commit real secrets. Restart sidecar after changing
            env.
          </p>
        </div>
      )}
    </div>
  );
}
