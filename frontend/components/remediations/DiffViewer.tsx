"use client";

import React from "react";
import { FileCode, Plus, Minus, Hash } from "lucide-react";

interface DiffViewerProps {
  diff: string;
  patchHash?: string;
}

export function DiffViewer({ diff, patchHash }: DiffViewerProps) {
  if (!diff || !diff.trim()) {
    return (
      <div className="rounded-lg border border-border-subtle bg-neutral-900/50 p-6 text-center text-sm text-neutral-400 font-mono">
        No unified diff content available.
      </div>
    );
  }

  // Parse lines into diff blocks
  const lines = diff.split("\n");
  let additions = 0;
  let deletions = 0;

  lines.forEach((line) => {
    if (line.startsWith("+") && !line.startsWith("+++")) additions++;
    if (line.startsWith("-") && !line.startsWith("---")) deletions++;
  });

  return (
    <div className="rounded-lg border border-border-subtle bg-neutral-950 overflow-hidden font-mono text-xs">
      {/* Diff Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-neutral-900/80 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-neutral-300">
          <FileCode className="h-4 w-4 text-emerald-400" />
          <span className="font-semibold text-white">Unified Code Patch</span>
          {patchHash && (
            <span className="text-[10px] text-neutral-500 flex items-center gap-1 bg-neutral-800/80 px-2 py-0.5 rounded border border-neutral-700/50">
              <Hash className="h-3 w-3" />
              SHA-256: {patchHash.slice(0, 12)}...
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1 text-emerald-400 font-bold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
            <Plus className="h-3 w-3" />
            {additions} lines
          </span>
          <span className="inline-flex items-center gap-1 text-rose-400 font-bold bg-rose-950/40 px-2 py-0.5 rounded border border-rose-800/40">
            <Minus className="h-3 w-3" />
            {deletions} lines
          </span>
        </div>
      </div>

      {/* Code Lines Viewer */}
      <div className="overflow-x-auto max-h-[500px] p-2 space-y-0.5 select-text">
        {lines.map((line, index) => {
          let lineStyle = "text-neutral-300 bg-transparent";
          let prefixSymbol = " ";

          if (line.startsWith("--- ") || line.startsWith("+++ ")) {
            lineStyle = "text-neutral-400 bg-neutral-900/60 font-semibold px-2 py-1 my-1 rounded border border-neutral-800";
            prefixSymbol = "";
          } else if (line.startsWith("@@ ")) {
            lineStyle = "text-cyan-400 bg-cyan-950/20 font-bold px-2 py-0.5 my-1 rounded border-l-2 border-cyan-500";
            prefixSymbol = "";
          } else if (line.startsWith("+") && !line.startsWith("+++")) {
            lineStyle = "text-emerald-300 bg-emerald-950/30 border-l-2 border-emerald-500";
            prefixSymbol = "+";
          } else if (line.startsWith("-") && !line.startsWith("---")) {
            lineStyle = "text-rose-300 bg-rose-950/30 border-l-2 border-rose-500";
            prefixSymbol = "-";
          }

          return (
            <div
              key={index}
              className={`flex items-start px-2 py-0.5 leading-relaxed transition-colors hover:bg-neutral-800/30 ${lineStyle}`}
            >
              <span className="w-8 shrink-0 text-neutral-600 select-none text-right pr-3 font-mono text-[10px]">
                {index + 1}
              </span>
              <pre className="whitespace-pre-wrap break-all font-mono m-0 flex-1">
                {line}
              </pre>
            </div>
          );
        })}
      </div>
    </div>
  );
}
