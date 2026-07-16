import { AlertCircle, CheckCircle2, Info } from "lucide-react";

const ICONS = { error: AlertCircle, info: Info, success: CheckCircle2 };

export function StatusMessage({ children, tone = "info" }) {
  const Icon = ICONS[tone] || Info;
  return (
    <div className={`nt-status nt-status--${tone}`} role={tone === "error" ? "alert" : "status"}>
      <Icon size={17} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}
