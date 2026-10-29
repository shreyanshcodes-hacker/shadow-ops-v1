import React from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from "lucide-react";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "warning" | "error" | "success";
  title?: string;
  onClose?: () => void;
}

export function Alert({
  className,
  variant = "info",
  title,
  children,
  onClose,
  ...props
}: AlertProps) {
  const icons = {
    info: <Info className="h-4 w-4 text-blue-400 shrink-0" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />,
    error: <AlertCircle className="h-4 w-4 text-red-400 shrink-0" />,
    success: <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />,
  };

  const variants = {
    info: "bg-blue-950/30 border-blue-800/50 text-blue-200",
    warning: "bg-amber-950/30 border-amber-800/50 text-amber-200",
    error: "bg-red-950/30 border-red-800/50 text-red-200",
    success: "bg-emerald-950/30 border-emerald-800/50 text-emerald-200",
  };

  return (
    <div
      role="alert"
      className={cn(
        "relative flex items-start gap-3 rounded-lg border p-4 text-sm",
        variants[variant],
        className
      )}
      {...props}
    >
      <div className="pt-0.5">{icons[variant]}</div>
      <div className="flex-1 space-y-1">
        {title && <h5 className="font-semibold tracking-tight">{title}</h5>}
        <div className="text-xs leading-relaxed opacity-90">{children}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-neutral-400 hover:text-neutral-100 transition-colors -mr-1 -mt-1 p-1"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
