import React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export function LoadingSpinner({
  className,
  size = "md",
}: {
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  const sizeMap = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-10 w-10",
  };

  return (
    <div className={cn("flex items-center justify-center p-4", className)}>
      <Loader2 className={cn("animate-spin text-crimson", sizeMap[size])} />
    </div>
  );
}
