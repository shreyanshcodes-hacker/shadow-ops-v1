import React from "react";
import { cn } from "@/lib/utils";
import { ShieldAlert, Plus } from "lucide-react";
import { Button } from "./Button";

export interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center p-8 border border-dashed border-border-muted rounded-xl bg-background/50",
        className
      )}
    >
      <div className="h-12 w-12 rounded-full bg-background-tertiary flex items-center justify-center text-neutral-400 mb-4 border border-border-subtle">
        {icon || <ShieldAlert className="h-6 w-6 text-neutral-400" />}
      </div>
      <h4 className="text-base font-semibold text-white mb-1">{title}</h4>
      <p className="text-xs text-neutral-400 max-w-sm mb-6">{description}</p>
      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          <Plus className="h-4 w-4" />
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
