import { cn } from "@/lib/cn";

export function Badge({ children, className = "", icon: Icon, tone = "accent" }) {
  return (
    <span className={cn("nt-badge", `nt-badge--${tone}`, className)}>
      {Icon ? <Icon size={13} aria-hidden="true" /> : null}
      {children}
    </span>
  );
}
