import React from "react";
import { cn } from "@/lib/utils";
import { AlertOctagon, RotateCcw } from "lucide-react";
import { Button } from "./Button";

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "System Operation Failed",
  message,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center p-8 border border-red-900/40 rounded-xl bg-red-950/10",
        className
      )}
    >
      <div className="h-12 w-12 rounded-full bg-red-950/40 flex items-center justify-center text-red-400 mb-4 border border-red-800/40">
        <AlertOctagon className="h-6 w-6 text-red-400" />
      </div>
      <h4 className="text-base font-semibold text-white mb-1">{title}</h4>
      <p className="text-xs text-red-300/80 max-w-sm mb-6 font-mono">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RotateCcw className="h-4 w-4" />
          Retry Operation
        </Button>
      )}
    </div>
  );
}
