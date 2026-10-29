import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "critical" | "high" | "medium" | "low" | "info" | "success" | "outline";
}

export function Badge({
  className,
  variant = "default",
  children,
  ...props
}: BadgeProps) {
  const variants = {
    default: "bg-background-elevated text-neutral-300 border border-border-subtle",
    critical: "bg-red-950/60 text-red-300 border border-red-700/60 font-semibold",
    high: "bg-orange-950/60 text-orange-300 border border-orange-700/60",
    medium: "bg-amber-950/60 text-amber-300 border border-amber-700/60",
    low: "bg-blue-950/60 text-blue-300 border border-blue-700/60",
    info: "bg-neutral-900 text-neutral-400 border border-neutral-700",
    success: "bg-emerald-950/60 text-emerald-300 border border-emerald-700/60",
    outline: "bg-transparent text-neutral-300 border border-border-muted",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-mono tracking-tight",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
