import React from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  className,
}: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className={cn(
          "w-full max-w-lg rounded-xl border border-border-muted bg-background-secondary p-6 shadow-2xl relative",
          className
        )}
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-neutral-400 hover:text-white transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-white tracking-tight">{title}</h2>
          {description && (
            <p className="text-xs text-neutral-400 mt-1">{description}</p>
          )}
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}
