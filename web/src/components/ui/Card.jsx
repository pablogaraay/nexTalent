import { cn } from "@/lib/cn";

export function Card({ as: Element = "section", children, className = "", elevated = false, tone = "default", ...props }) {
  return (
    <Element className={cn("nt-card", `nt-card--${tone}`, elevated && "nt-card--elevated", className)} {...props}>
      {children}
    </Element>
  );
}
