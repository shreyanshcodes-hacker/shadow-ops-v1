"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Sliders,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  RefreshCw,
  GitCommit,
  CheckCircle2,
  Layers,
} from "lucide-react";

import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { AttackPath, RiskBand } from "@/types";

export default function AttackPathsPage() {
  const { activeWorkspace } = useWorkspace();
  const [paths, setPaths] = useState<AttackPath[]>([]);
  const [loading, setLoading] = useState(true);
  const [synthesizing, setSynthesizing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAttackPaths = useCallback(async () => {
    if (!activeWorkspace) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<AttackPath[]>(
        `/attack-paths?workspace_id=${activeWorkspace.id}`
      );
      setPaths(data);
    } catch (err: unknown) {
      console.error("Failed to load attack paths", err);
      setError("Unable to retrieve attack paths. Please ensure workspace is accessible.");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    fetchAttackPaths();
  }, [fetchAttackPaths]);

  const handleSynthesize = async () => {
    if (!activeWorkspace) return;
    try {
      setSynthesizing(true);
      const newPaths = await apiClient.post<AttackPath[]>(
        `/attack-paths/synthesize?workspace_id=${activeWorkspace.id}`
      );
      setPaths(newPaths);
    } catch (err: unknown) {
      console.error("Failed to synthesize attack paths", err);
      alert("Failed to synthesize attack paths from relationships.");
    } finally {
      setSynthesizing(false);
    }
  };

  const getRiskBandBadge = (band: RiskBand | null | undefined, score?: number | null) => {
    switch (band) {
      case "CRITICAL":
        return "bg-crimson/20 text-crimson-light border-crimson/40";
      case "HIGH":
        return "bg-amber-950/40 text-amber-300 border-amber-600/40";
      case "MEDIUM":
        return "bg-yellow-950/40 text-yellow-300 border-yellow-600/40";
      case "LOW":
        return "bg-blue-950/40 text-blue-300 border-blue-600/40";
      default:
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
    }
  };

  return (
    <CommandCenterShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-subtle pb-5">
          <div>
            <div className="flex items-center gap-2">
              <Sliders className="h-6 w-6 text-crimson" />
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Attack Path Intelligence
              </h1>
            </div>
            <p className="text-sm text-neutral-400 mt-1">
              Deterministic attack graph progression and auditable risk scoring (Model: risk-v1).
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSynthesize}
              disabled={synthesizing || loading}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-md bg-crimson hover:bg-crimson-hover text-white transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${synthesizing ? "animate-spin" : ""}`} />
              {synthesizing ? "Synthesizing..." : "Synthesize Paths"}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-950/30 border border-red-800 text-red-200 text-sm flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Stats Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-background-secondary border border-border-subtle">
            <div className="text-xs font-mono text-neutral-400">TOTAL ATTACK PATHS</div>
            <div className="text-2xl font-bold text-white mt-1">{paths.length}</div>
            <div className="text-[11px] text-neutral-400 mt-1 flex items-center gap-1">
              <Layers className="h-3 w-3" /> Workspace multi-step graphs
            </div>
          </div>

          <div className="p-4 rounded-lg bg-background-secondary border border-border-subtle">
            <div className="text-xs font-mono text-neutral-400">CRITICAL RISK PATHS</div>
            <div className="text-2xl font-bold text-crimson-light mt-1">
              {paths.filter((p) => p.risk_band === "CRITICAL").length}
            </div>
            <div className="text-[11px] text-neutral-400 mt-1 flex items-center gap-1">
              <ShieldAlert className="h-3 w-3 text-crimson" /> Requires urgent mitigation
            </div>
          </div>

          <div className="p-4 rounded-lg bg-background-secondary border border-border-subtle">
            <div className="text-xs font-mono text-neutral-400">HIGH RISK PATHS</div>
            <div className="text-2xl font-bold text-amber-300 mt-1">
              {paths.filter((p) => p.risk_band === "HIGH").length}
            </div>
            <div className="text-[11px] text-neutral-400 mt-1 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-amber-400" /> Elevated compromise potential
            </div>
          </div>

          <div className="p-4 rounded-lg bg-background-secondary border border-border-subtle">
            <div className="text-xs font-mono text-neutral-400">RISK ENGINE MODEL</div>
            <div className="text-xl font-bold text-emerald-400 mt-1 font-mono">risk-v1</div>
            <div className="text-[11px] text-neutral-400 mt-1 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" /> 100% Deterministic & Auditable
            </div>
          </div>
        </div>

        {/* Path List */}
        {loading ? (
          <div className="p-12 text-center text-neutral-400 bg-background-secondary rounded-lg border border-border-subtle">
            <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-crimson" />
            Loading attack paths...
          </div>
        ) : paths.length === 0 ? (
          <div className="p-12 text-center bg-background-secondary rounded-lg border border-border-subtle">
            <Sliders className="h-10 w-10 text-neutral-400 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-white">No Attack Paths Discovered Yet</h3>
            <p className="text-sm text-neutral-400 max-w-md mx-auto mt-1 mb-4">
              Attack paths are synthesized when security relationships are identified between findings on authorized assets.
            </p>
            <button
              onClick={handleSynthesize}
              disabled={synthesizing}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-md bg-crimson hover:bg-crimson-hover text-white transition-colors"
            >
              <RefreshCw className={`h-4 w-4 ${synthesizing ? "animate-spin" : ""}`} />
              Run Path Synthesis
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {paths.map((p) => (
              <Link
                key={p.id}
                href={`/attack-paths/${p.id}`}
                className="block p-5 rounded-lg bg-background-secondary border border-border-subtle hover:border-neutral-700 transition-all group"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded font-mono font-semibold border ${getRiskBandBadge(
                          p.risk_band,
                          p.risk_score
                        )}`}
                      >
                        {p.risk_band || "CALCULATING"}
                      </span>
                      <span className="text-xs font-mono text-neutral-400 bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800">
                        SCORE: {p.risk_score !== null && p.risk_score !== undefined ? p.risk_score.toFixed(1) : "N/A"}/100
                      </span>
                      <span className="text-xs font-mono text-neutral-400 flex items-center gap-1">
                        <GitCommit className="h-3.5 w-3.5" /> {p.node_count} nodes &bull; {p.edge_count} transitions
                      </span>
                    </div>

                    <h2 className="text-base font-semibold text-white group-hover:text-crimson-light transition-colors">
                      {p.title || p.name}
                    </h2>
                    <p className="text-xs text-neutral-400 line-clamp-2">
                      {p.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-400 pt-1 font-mono">
                      <div>
                        Entry: <span className="text-neutral-200">{p.entry_point || "External / Unauthenticated"}</span>
                      </div>
                      <div>
                        Target: <span className="text-neutral-200">{p.target_asset || "Backend Component"}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                    <div className="text-right hidden sm:block">
                      <div className="text-xs font-mono text-neutral-400">MODEL</div>
                      <div className="text-xs font-mono text-neutral-300">{p.model_version}</div>
                    </div>
                    <div className="h-8 w-8 rounded-full bg-neutral-900 border border-neutral-800 flex items-center justify-center text-neutral-400 group-hover:text-white group-hover:border-crimson transition-colors">
                      <ArrowRight className="h-4 w-4" />
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </CommandCenterShell>
  );
}
