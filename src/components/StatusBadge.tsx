export default function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  let cls = "idle";
  if (["ok", "ready", "connected", "completed", "installed"].includes(s)) cls = "ok";
  else if (["downloading", "running", "queued", "needs_config"].includes(s)) cls = "warn";
  else if (["error", "failed", "disconnected"].includes(s)) cls = "err";
  return <span className={`badge ${cls}`}>{status}</span>;
}
