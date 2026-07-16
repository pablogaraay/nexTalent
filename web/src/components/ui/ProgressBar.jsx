export function ProgressBar({ label, tone = "accent", value = 0 }) {
  const safeValue = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="nt-progress" aria-label={label}>
      <div className="nt-progress__track">
        <div className={`nt-progress__fill nt-progress__fill--${tone}`} style={{ width: `${safeValue}%` }} />
      </div>
      {label ? <span className="nt-progress__label">{label}</span> : null}
    </div>
  );
}
