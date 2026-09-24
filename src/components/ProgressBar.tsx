export default function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="progress" title={`${pct}%`}>
      <span style={{ width: `${pct}%` }} />
    </div>
  );
}
