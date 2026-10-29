"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Sliders,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  RefreshCw,
  GitCommit,
  CheckCircle2,
  ExternalLink,
  History,
  Lock,
  Layers,
} from "lucide-react";

import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { apiClient } from "@/lib/api-client";
import { AttackPathDetail, RiskBand } from "@/types";

export default function AttackPathDetailPage() {
  const params = useParams();
  const pathId = params?.id as string;

  const [path, setPath] = useState<AttackPathDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPathDetails = useCallback(async () => {
    if (!pathId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<AttackPathDetail>(`/attack-paths/${pathId}`);
      setPath(data);
    } catch (err: unknown) {
      console.error("Failed to load attack path details", err);
      setError("Unable to retrieve attack path details.");
    } finally {
      setLoading(false);
    }
  }, [pathId]);

  useEffect(() => {
    fetchPathDetails();
  }, [fetchPathDetails]);

  const handleRecalculateRisk = async () => {
    if (!pathId) return;
    try {
      setRecalculating(true);
      await apiClient.post(`/attack-paths/${pathId}/recalculate-risk`);
      await fetchPathDetails();
    } catch (err: unknown) {
      console.error("Failed to recalculate risk", err);
      alert("Failed to recalculate risk score.");
    } finally {
      setRecalculating(false);
    }
  };

  const getRiskBandBadge = (band: RiskBand | null | undefined) => {
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

  const getSeverityBadge = (severity?: string | null) => {
    switch (severity?.toLowerCase()) {
      case "critical":
        return "bg-crimson/20 text-crimson-light border-crimson/40";
      case "high":
        return "bg-amber-950/40 text-amber-300 border-amber-600/40";
      case "medium":
        return "bg-yellow-950/40 text-yellow-300 border-yellow-600/40";
      case "low":
        return "bg-blue-950/40 text-blue-300 border-blue-600/40";
      default:
        return "bg-neutral-800 text-neutral-400 border-neutral-700";
    }
  };

  if (loading) {
    return (
      <CommandCenterShell>
        <div className="p-12 text-center text-neutral-400 bg-background-secondary rounded-lg border border-border-subtle">
          <RefreshCw className="h-6 w-6 animate-spin mx-auto mb-2 text-crimson" />
          Loading attack path graph & risk factors...
        </div>
      </CommandCenterShell>
    );
  }

  if (error || !path) {
    return (
      <CommandCenterShell>
        <div className="space-y-4">
          <Link
            href="/attack-paths"
            className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Attack Paths
          </Link>
          <div className="p-6 rounded-lg bg-red-950/30 border border-red-800 text-red-200 text-sm flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
            <span>{error || "Attack path not found."}</span>
          </div>
        </div>
      </CommandCenterShell>
    );
  }

  const factors = path.factors || {};

  return (
    <CommandCenterShell>
      <div className="space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link
            href="/attack-paths"
            className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Attack Paths
          </Link>

          <div className="flex items-center gap-2">
            <Link
              href="/security-team"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-crimson/20 hover:bg-crimson/30 text-crimson-light border border-crimson/40 transition-colors"
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>AI Security Team</span>
            </Link>

            <button
              onClick={handleRecalculateRisk}
              disabled={recalculating}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium rounded-md bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${recalculating ? "animate-spin" : ""}`} />
              {recalculating ? "Recalculating..." : "Recalculate Risk"}
            </button>
          </div>
        </div>

        {/* Header Card */}
        <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`text-xs px-2.5 py-0.5 rounded font-mono font-semibold border ${getRiskBandBadge(
                    path.risk_band
                  )}`}
                >
                  {path.risk_band} RISK
                </span>
                <span className="text-xs font-mono text-neutral-400 bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800">
                  STATUS: {path.status.toUpperCase()}
                </span>
                <span className="text-xs font-mono text-neutral-400 bg-neutral-900 px-2 py-0.5 rounded border border-neutral-800">
                  MODEL: {path.model_version}
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                {path.title || path.name}
              </h1>
              <p className="text-xs sm:text-sm text-neutral-400 max-w-3xl">
                {path.description}
              </p>
            </div>

            {/* Risk Meter */}
            <div className="p-4 rounded-lg bg-neutral-900/80 border border-neutral-800 flex items-center gap-4 shrink-0">
              <div className="text-center">
                <div className="text-[10px] font-mono text-neutral-400 tracking-wider">DETERMINISTIC SCORE</div>
                <div className="text-3xl font-black text-crimson-light font-mono mt-0.5">
                  {path.risk_score !== null && path.risk_score !== undefined
                    ? path.risk_score.toFixed(1)
                    : "N/A"}
                  <span className="text-xs text-neutral-400 font-normal"> / 100</span>
                </div>
              </div>
              <div className="h-10 w-px bg-neutral-800" />
              <div className="text-xs font-mono text-neutral-400 space-y-0.5">
                <div>Nodes: <span className="text-white font-bold">{path.nodes?.length || 0}</span></div>
                <div>Transitions: <span className="text-white font-bold">{path.edges?.length || 0}</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* Visual Attack Path Graph Sequence */}
        <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-crimson" />
              <h2 className="text-base font-semibold text-white">Visual Attack Graph Sequence</h2>
            </div>
            <span className="text-xs font-mono text-neutral-400">
              {path.nodes?.length || 0} Sequential Steps
            </span>
          </div>

          <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3 overflow-x-auto py-4">
            {path.nodes?.map((node, index) => {
              const edge = path.edges?.find((e) => e.source_node_id === node.id);
              return (
                <React.Fragment key={node.id}>
                  {/* Node Card */}
                  <div className="flex-1 min-w-[240px] p-4 rounded-lg bg-neutral-900 border border-neutral-800 hover:border-neutral-700 transition-colors space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 font-bold">
                        STEP {node.node_order + 1}
                      </span>
                      {node.finding_severity && (
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase ${getSeverityBadge(
                            node.finding_severity
                          )}`}
                        >
                          {node.finding_severity}
                        </span>
                      )}
                    </div>

                    <div className="font-medium text-xs text-white line-clamp-2">
                      {node.label}
                    </div>

                    {node.finding_id && (
                      <Link
                        href={`/findings/${node.finding_id}`}
                        className="inline-flex items-center gap-1 text-[11px] text-crimson-light hover:underline pt-1"
                      >
                        Inspect Finding <ExternalLink className="h-3 w-3" />
                      </Link>
                    )}
                  </div>

                  {/* Transition Arrow / Edge */}
                  {index < (path.nodes?.length || 0) - 1 && (
                    <div className="flex md:flex-col items-center justify-center text-neutral-400 shrink-0 px-1 py-2 md:py-0">
                      <div className="text-[10px] font-mono text-amber-400 px-1.5 py-0.5 rounded bg-amber-950/30 border border-amber-900/50 mb-1 hidden md:block">
                        {edge?.edge_type || "TRANSITIONS"}
                      </div>
                      <ArrowRight className="h-4 w-4 text-crimson hidden md:block" />
                      <div className="text-xs md:hidden flex items-center gap-1 text-amber-400">
                        &darr; {edge?.edge_type || "TRANSITIONS"}
                      </div>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Deterministic Risk Breakdown (Model: risk-v1) */}
        <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <div className="flex items-center gap-2">
              <Lock className="h-5 w-5 text-emerald-400" />
              <h2 className="text-base font-semibold text-white">
                Deterministic Risk Factor Breakdown (Model: {path.model_version})
              </h2>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800">
              AUDITABLE ALGORITHM
            </span>
          </div>

          <p className="text-xs text-neutral-400">
            The final score is mathematically calculated from 6 auditable security dimensions.
            AI output is advisory; this deterministic score cannot be altered or overridden by external LLMs.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {/* 1. Finding Severity */}
            <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-neutral-400">FINDING SEVERITY (30%)</span>
                <span className="font-mono font-bold text-white">
                  {factors.finding_severity?.score?.toFixed(1) ?? "N/A"}/100
                </span>
              </div>
              <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-crimson h-full rounded-full"
                  style={{ width: `${Math.min(100, factors.finding_severity?.score || 0)}%` }}
                />
              </div>
              <div className="text-[11px] text-neutral-400">
                Contribution: +{factors.finding_severity?.contribution?.toFixed(1) ?? "0.0"} pts
              </div>
              <div className="text-[11px] text-neutral-400">
                {factors.finding_severity?.details || "Based on max vulnerability severity."}
              </div>
            </div>

            {/* 2. Exploitability */}
            <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-neutral-400">EXPLOITABILITY (20%)</span>
                <span className="font-mono font-bold text-white">
                  {factors.exploitability?.score?.toFixed(1) ?? "N/A"}/100
                </span>
              </div>
              <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-amber-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, factors.exploitability?.score || 0)}%` }}
                />
              </div>
              <div className="text-[11px] text-neutral-400">
                Contribution: +{factors.exploitability?.contribution?.toFixed(1) ?? "0.0"} pts
              </div>
              <div className="text-[11px] text-neutral-400">
                {factors.exploitability?.details || "Based on edge likelihood & amplification."}
              </div>
            </div>

            {/* 3. Asset Criticality */}
            <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-neutral-400">ASSET CRITICALITY (20%)</span>
                <span className="font-mono font-bold text-white">
                  {factors.asset_criticality?.score?.toFixed(1) ?? "N/A"}/100
                </span>
              </div>
              <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-blue-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, factors.asset_criticality?.score || 0)}%` }}
                />
              </div>
              <div className="text-[11px] text-neutral-400">
                Contribution: +{factors.asset_criticality?.contribution?.toFixed(1) ?? "0.0"} pts
              </div>
              <div className="text-[11px] text-neutral-400">
                {factors.asset_criticality?.details || "Target asset business tier."}
              </div>
            </div>

            {/* 4. Confidence */}
            <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-neutral-400">CONFIDENCE (15%)</span>
                <span className="font-mono font-bold text-white">
                  {factors.confidence?.score?.toFixed(1) ?? "N/A"}/100
                </span>
              </div>
              <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-purple-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, factors.confidence?.score || 0)}%` }}
                />
              </div>
              <div className="text-[11px] text-neutral-400">
                Contribution: +{factors.confidence?.contribution?.toFixed(1) ?? "0.0"} pts
              </div>
              <div className="text-[11px] text-neutral-400">
                {factors.confidence?.details || "Averaged node & relationship confidence."}
              </div>
            </div>

            {/* 5. Exposure */}
            <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-neutral-400">EXPOSURE (10%)</span>
                <span className="font-mono font-bold text-white">
                  {factors.exposure?.score?.toFixed(1) ?? "N/A"}/100
                </span>
              </div>
              <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-rose-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, factors.exposure?.score || 0)}%` }}
                />
              </div>
              <div className="text-[11px] text-neutral-400">
                Contribution: +{factors.exposure?.contribution?.toFixed(1) ?? "0.0"} pts
              </div>
              <div className="text-[11px] text-neutral-400">
                {factors.exposure?.details || "Perimeter and network exposure."}
              </div>
            </div>

            {/* 6. Path Complexity */}
            <div className="p-4 rounded-lg bg-neutral-900 border border-neutral-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-neutral-400">PATH COMPLEXITY (5%)</span>
                <span className="font-mono font-bold text-white">
                  {factors.path_complexity?.score?.toFixed(1) ?? "N/A"}/100
                </span>
              </div>
              <div className="w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-teal-500 h-full rounded-full"
                  style={{ width: `${Math.min(100, factors.path_complexity?.score || 0)}%` }}
                />
              </div>
              <div className="text-[11px] text-neutral-400">
                Contribution: +{factors.path_complexity?.contribution?.toFixed(1) ?? "0.0"} pts
              </div>
              <div className="text-[11px] text-neutral-400">
                {factors.path_complexity?.details || "Short paths represent higher risk."}
              </div>
            </div>
          </div>
        </div>

        {/* Step-by-Step Execution Sequence */}
        <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
            <GitCommit className="h-5 w-5 text-crimson" />
            <h2 className="text-base font-semibold text-white">Step-by-Step Progression</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-neutral-900 text-neutral-400 font-mono border-b border-neutral-800">
                <tr>
                  <th className="py-2.5 px-3">STEP</th>
                  <th className="py-2.5 px-3">VULNERABILITY / NODE</th>
                  <th className="py-2.5 px-3">TYPE</th>
                  <th className="py-2.5 px-3">SEVERITY</th>
                  <th className="py-2.5 px-3">TRANSITION TO NEXT</th>
                  <th className="py-2.5 px-3 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800 font-mono">
                {path.nodes?.map((node, index) => {
                  const edge = path.edges?.find((e) => e.source_node_id === node.id);
                  return (
                    <tr key={node.id} className="hover:bg-neutral-900/50">
                      <td className="py-3 px-3 font-bold text-white">#{node.node_order + 1}</td>
                      <td className="py-3 px-3 font-sans">
                        <div className="font-semibold text-neutral-200">{node.label}</div>
                        {node.description && (
                          <div className="text-[11px] text-neutral-400 mt-0.5 line-clamp-1">
                            {node.description}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-3 uppercase text-neutral-400">{node.node_type}</td>
                      <td className="py-3 px-3">
                        {node.finding_severity ? (
                          <span
                            className={`px-2 py-0.5 rounded border uppercase text-[10px] ${getSeverityBadge(
                              node.finding_severity
                            )}`}
                          >
                            {node.finding_severity}
                          </span>
                        ) : (
                          "N/A"
                        )}
                      </td>
                      <td className="py-3 px-3 text-amber-300">
                        {edge ? (
                          <span>
                            {edge.edge_type.toUpperCase()} &rarr;
                          </span>
                        ) : (
                          <span className="text-neutral-400 font-normal">Final Target Reached</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {node.finding_id && (
                          <Link
                            href={`/findings/${node.finding_id}`}
                            className="inline-flex items-center gap-1 text-crimson-light hover:underline font-sans"
                          >
                            View Finding <ArrowRight className="h-3 w-3" />
                          </Link>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Risk Calculation Snapshot History */}
        <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle space-y-4">
          <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
            <History className="h-5 w-5 text-neutral-400" />
            <h2 className="text-base font-semibold text-white">Risk Calculation Snapshot History</h2>
          </div>

          {path.risk_snapshots && path.risk_snapshots.length > 0 ? (
            <div className="space-y-2">
              {path.risk_snapshots.map((snap) => (
                <div
                  key={snap.id}
                  className="p-3 rounded-lg bg-neutral-900 border border-neutral-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded border text-[10px] font-bold ${getRiskBandBadge(
                        snap.risk_band
                      )}`}
                    >
                      {snap.risk_band} ({snap.score.toFixed(1)})
                    </span>
                    <span className="text-neutral-400">
                      Calculated: {new Date(snap.calculated_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-neutral-400">
                    Engine: <span className="text-neutral-200">{snap.calculated_by}</span> (v{snap.model_version})
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-neutral-400">No snapshot history recorded yet.</p>
          )}
        </div>
      </div>
    </CommandCenterShell>
  );
}
