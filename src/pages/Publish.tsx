import { useEffect, useState } from "react";
import { api, Job, PlatformInfo, YtStatus, XStatus } from "../api/client";
import StatusBadge from "../components/StatusBadge";

export default function PublishPage() {
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [yt, setYt] = useState<YtStatus | null>(null);
  const [x, setX] = useState<XStatus | null>(null);
  const [privacy, setPrivacy] = useState("private");
  const [xText, setXText] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const [plat, ytStatus, xStatus, j] = await Promise.all([
        api.listPlatforms(),
        api.youtubeStatus(),
        api.xStatus(),
        api.listJobs(),
      ]);
      setPlatforms(plat.platforms);
      setYt(ytStatus);
      setX(xStatus);
      setJobs(j.jobs.filter((x) => x.status === "completed" && x.output?.video));
    } catch (e: unknown) {
      setMsg(String((e as Error).message || e));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    const job = jobs.find((j) => j.id === selected);
    if (job?.output?.title && !xText) {
      setXText((job.output.title || job.topic).slice(0, 270));
    }
  }, [selected, jobs, xText]);

  return (
    <div>
      <h1 className="page-title">Publish</h1>
      <p className="page-sub">
        Connect platforms and publish finished videos. YouTube and X are live; TikTok / Instagram coming soon.
      </p>

      <div className="card">
        <h3>Connected platforms</h3>
        <div className="platform-grid">
          {(platforms.length
            ? platforms
            : [
                { id: "youtube", name: "YouTube", status: yt?.status || "…", detail: yt?.channel_name, available: true },
                { id: "x", name: "X (Twitter)", status: x?.status || "…", detail: x?.username, available: true },
                { id: "tiktok", name: "TikTok", status: "coming_soon", detail: "Coming soon", available: false },
                { id: "instagram", name: "Instagram", status: "coming_soon", detail: "Coming soon", available: false },
              ]
          ).map((p) => (
            <div key={p.id} className={`platform-card${!p.available ? " soon" : ""}`}>
              <div className="row">
                <strong>{p.name}</strong>
                <StatusBadge status={p.status} />
              </div>
              <p className="muted" style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
                {p.detail || (p.available ? "Not connected" : "Coming soon")}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>YouTube</h3>
          {yt && (
            <p>
              <StatusBadge status={yt.status} />{" "}
              {yt.channel_name && <strong>{yt.channel_name}</strong>}
              {yt.error && <span className="err-text"> — {yt.error}</span>}
            </p>
          )}
          <div className="row">
            <button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setMsg("");
                try {
                  setYt(await api.youtubeConnect());
                  setMsg("YouTube connected.");
                  refresh();
                } catch (e: unknown) {
                  setMsg(String((e as Error).message || e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Connect YouTube
            </button>
            <button
              className="ghost"
              onClick={async () => {
                setYt(await api.youtubeDisconnect());
                refresh();
              }}
            >
              Disconnect
            </button>
          </div>
        </div>

        <div className="card">
          <h3>X (Twitter)</h3>
          {x && (
            <p>
              <StatusBadge status={x.status} />{" "}
              {x.username && <strong>@{x.username}</strong>}
              {x.error && <span className="err-text"> — {x.error}</span>}
            </p>
          )}
          <p className="muted" style={{ fontSize: "0.85rem" }}>
            Uses OAuth 1.0a keys from <code>.env</code> (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN,
            X_ACCESS_TOKEN_SECRET). Media upload via v1.1 + tweet via API v2.
          </p>
          <button className="ghost" onClick={refresh}>
            Refresh X status
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Publish a completed job</h3>
        <div className="field">
          <label>Job</label>
          <select
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value);
              setXText("");
            }}
          >
            <option value="">Select…</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                [{j.mode || "explainer"}] {j.topic} — {j.output?.title || j.id}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>YouTube privacy</label>
          <select value={privacy} onChange={(e) => setPrivacy(e.target.value)}>
            <option value="private">Private</option>
            <option value="unlisted">Unlisted</option>
            <option value="public">Public</option>
          </select>
        </div>
        <div className="field">
          <label>X post text</label>
          <textarea
            rows={3}
            value={xText}
            onChange={(e) => setXText(e.target.value.slice(0, 280))}
            placeholder="Caption for X (max 280)"
          />
          <div className="muted" style={{ fontSize: "0.75rem" }}>
            {xText.length}/280
          </div>
        </div>
        <div className="row">
          <button
            disabled={!selected || busy}
            onClick={async () => {
              const job = jobs.find((j) => j.id === selected);
              if (!job?.output?.video) return;
              setBusy(true);
              setMsg("Uploading to YouTube…");
              try {
                const r = await api.youtubeUpload({
                  video_path: job.output.video,
                  title: job.output.title || job.topic,
                  description: job.output.description || "Created with AutoReel Studio",
                  tags: job.output.tags,
                  privacy,
                  thumbnail_path: job.output.thumbnail,
                });
                setMsg(`YouTube: ${r.url}`);
              } catch (e: unknown) {
                setMsg(String((e as Error).message || e));
              } finally {
                setBusy(false);
              }
            }}
          >
            Upload to YouTube
          </button>
          <button
            disabled={!selected || busy || !xText.trim()}
            onClick={async () => {
              const job = jobs.find((j) => j.id === selected);
              if (!job?.output?.video) return;
              setBusy(true);
              setMsg("Publishing to X…");
              try {
                const r = await api.xPublish({
                  video_path: job.output.video,
                  text: xText.trim(),
                });
                setMsg(r.url ? `X: ${r.url}` : r.message || "Posted to X");
              } catch (e: unknown) {
                setMsg(String((e as Error).message || e));
              } finally {
                setBusy(false);
              }
            }}
          >
            Post to X
          </button>
          <button className="ghost" disabled title="Coming soon">
            TikTok (soon)
          </button>
          <button className="ghost" disabled title="Coming soon">
            Instagram (soon)
          </button>
          <button className="ghost" onClick={refresh}>
            Refresh
          </button>
        </div>
        {msg && <p className="muted">{msg}</p>}
      </div>
    </div>
  );
}
