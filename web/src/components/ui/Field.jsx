import { cn } from "@/lib/cn";

export function Field({ children, className = "", hint, id, label }) {
  return (
    <div className={cn("nt-field", className)}>
      <label htmlFor={id} className="nt-field__label">{label}</label>
      {children}
      {hint ? <p className="nt-field__hint">{hint}</p> : null}
    </div>
  );
}
