import { LoaderCircle } from "lucide-react";

import { cn } from "@/lib/cn";

export function Button({
  children,
  className = "",
  disabled = false,
  icon: Icon,
  loading = false,
  size = "md",
  variant = "primary",
  type = "button",
  ...props
}) {
  return (
    <button
      type={type}
      className={cn("nt-button", `nt-button--${variant}`, `nt-button--${size}`, className)}
      {...props}
      disabled={loading || disabled}
      aria-busy={loading || undefined}
    >
      {loading ? <LoaderCircle size={16} className="animate-spin" aria-hidden="true" /> : Icon ? <Icon size={16} aria-hidden="true" /> : null}
      <span>{children}</span>
    </button>
  );
}
