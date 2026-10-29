"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Shield,
  Bot,
  Users,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Play,
  RotateCw,
  Search,
  Sliders,
  Layers,
  FileCheck,
} from "lucide-react";

import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { SecurityTeamRun, Asset, Scan } from "@/types";

export default function SecurityTeamPage() {
  const { activeWorkspace } = useWorkspace();
  const [runs, setRuns] = useState<SecurityTeamRun[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [selectedScanId, setSelectedScanId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!activeWorkspace) return;
    try {
      setLoading(true);
      setError(null);
      const [runsData, assetsData, scansData] = await Promise.all([
        apiClient.get<SecurityTeamRun[]>(`/security-team/runs?workspace_id=${activeWorkspace.id}`),
        apiClient.get<Asset[]>(`/assets?workspace_id=${activeWorkspace.id}`),
        apiClient.get<Scan[]>(`/scans?workspace_id=${activeWorkspace.id}`),
      ]);
      setRuns(runsData);
      setAssets(assetsData);
      setScans(scansData);
      if (assetsData.length > 0 && !selectedAssetId) {
        setSelectedAssetId(assetsData[0].id);
      }
    } catch (err: unknown) {
      console.error("Failed to load security team runs", err);
      setError("Unable to retrieve security team runs for this workspace.");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace, selectedAssetId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleTriggerRun = async () => {
    if (!activeWorkspace || !selectedAssetId) return;
    try {
      setTriggering(true);
      const newRun = await apiClient.post<SecurityTeamRun>("/security-team/runs", {
        workspace_id: activeWorkspace.id,
        asset_id: selectedAssetId,
        scan_id: selectedScanId || null,
        orchestration_version: "security-team-v1",
      });
      setRuns((prev) => [newRun, ...prev]);
      setShowModal(false);
    } catch (err: unknown) {
      console.error("Failed to trigger security team evaluation", err);
      alert("Failed to trigger evaluation. Check asset authorization.");
    } finally {
      setTriggering(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SUCCEEDED":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-950/60 border border-emerald-700 text-emerald-400">SUCCEEDED</span>;
      case "RUNNING":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-cyan-950/60 border border-cyan-700 text-cyan-400 animate-pulse">RUNNING</span>;
      case "PARTIAL":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-amber-950/60 border border-amber-700 text-amber-400">PARTIAL</span>;
      case "QUEUED":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-blue-950/60 border border-blue-700 text-blue-400">QUEUED</span>;
      case "CANCELED":
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-neutral-800 border border-neutral-700 text-neutral-400">CANCELED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-mono bg-crimson/20 border border-crimson text-crimson-light">FAILED</span>;
    }
  };

  return (
    <CommandCenterShell>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border-subtle pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 text-[10px] font-mono uppercase bg-crimson/10 border border-crimson/30 text-crimson tracking-wider rounded">
                Stage 7 Architecture
              </span>
              <span className="text-xs text-neutral-500 font-mono">
                5-Agent Orchestration • Bounded Autonomy
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
              <Users className="h-6 w-6 text-crimson" />
              AI Security Team
            </h1>
            <p className="text-sm text-neutral-400 mt-1 max-w-2xl">
              Specialized collaborative security agents analyzing perimeter boundaries, vulnerability mechanics, exploit chains, and deterministic risk.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              disabled={loading}
              className="p-2 rounded border border-border-subtle bg-background-secondary hover:bg-neutral-800 text-neutral-300 transition-colors"
              title="Refresh runs"
            >
              <RotateCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>

            <button
              onClick={() => setShowModal(true)}
              disabled={loading || assets.length === 0}
              className="px-4 py-2 rounded bg-crimson hover:bg-crimson/90 text-white text-sm font-medium flex items-center gap-2 shadow-lg shadow-crimson/20 transition-all disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              Trigger Team Evaluation
            </button>
          </div>
        </div>

        {/* Safety Invariant Notice */}
        <div className="p-4 rounded-lg bg-background-secondary border border-border-subtle flex items-start gap-3">
          <Shield className="h-5 w-5 text-crimson shrink-0 mt-0.5" />
          <div className="text-xs text-neutral-300 space-y-1">
            <p className="font-semibold text-white">
              Analytical Workers Policy: Non-Autonomous AI Invariant
            </p>
            <p className="text-neutral-400 leading-relaxed">
              ShadowOps agents cannot execute shell commands, exploit targets, commit code, or alter deterministic risk engine calculations. All assessments are strictly advisory and require human engineer review before any operational actions.
            </p>
          </div>
        </div>

        {/* 5 Agent Roster Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {[
            { name: "RECON_AGENT", role: "Architecture & Perimeter", icon: Search, desc: "Surfaces exposed components, entry points, and boundaries." },
            { name: "VULNERABILITY_ANALYST", role: "Weakness Mechanics", icon: AlertTriangle, desc: "Examines exploit preconditions, impact, and missing evidence." },
            { name: "ATTACK_PATH_AGENT", role: "Exploit Progression", icon: Sliders, desc: "Evaluates multi-hop lateral movements and interconnects." },
            { name: "RISK_ANALYST", role: "Impact Context", icon: Layers, desc: "Explains deterministic risk-v1 factors and human priorities." },
            { name: "SECURITY_REVIEWER", role: "Executive Synthesis", icon: FileCheck, desc: "Synthesizes consensus and issues human review boundary." },
          ].map((agent, idx) => {
            const Icon = agent.icon;
            return (
              <div key={idx} className="p-3.5 rounded-lg bg-background-secondary border border-border-subtle flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="h-7 w-7 rounded bg-neutral-900 border border-neutral-700 flex items-center justify-center text-neutral-300">
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="font-mono text-xs font-semibold text-white">
                      {agent.name.replace("_AGENT", "")}
                    </span>
                  </div>
                  <p className="text-[11px] font-medium text-crimson-light mb-1">{agent.role}</p>
                  <p className="text-[11px] text-neutral-400 leading-tight">{agent.desc}</p>
                </div>
                <div className="mt-3 pt-2 border-t border-border-subtle/50 flex items-center justify-between text-[10px] text-neutral-500 font-mono">
                  <span>SPECIALIZED</span>
                  <span className="text-emerald-400">ACTIVE</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Evaluations List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Bot className="h-4 w-4 text-crimson" />
              Team Evaluations ({runs.length})
            </h2>
            <span className="text-xs text-neutral-500 font-mono">
              Workspace: {activeWorkspace?.name}
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-neutral-400 font-mono text-sm border border-border-subtle rounded-lg bg-background-secondary">
              <RotateCw className="h-5 w-5 animate-spin mx-auto mb-2 text-crimson" />
              Loading security team orchestrations...
            </div>
          ) : error ? (
            <div className="p-6 rounded-lg bg-crimson/10 border border-crimson/30 text-crimson text-sm">
              {error}
            </div>
          ) : runs.length === 0 ? (
            <div className="p-12 text-center border border-dashed border-border-subtle rounded-lg bg-background-secondary/50">
              <Bot className="h-10 w-10 text-neutral-600 mx-auto mb-3" />
              <h3 className="text-base font-medium text-white mb-1">No Security Team evaluations yet</h3>
              <p className="text-xs text-neutral-400 max-w-md mx-auto mb-4">
                Run the multi-agent AI Security Team across your authorized assets to synthesize findings into comprehensive risk assessments.
              </p>
              <button
                onClick={() => setShowModal(true)}
                disabled={assets.length === 0}
                className="px-4 py-2 rounded bg-crimson hover:bg-crimson/90 text-white text-xs font-medium inline-flex items-center gap-2"
              >
                <Play className="h-3.5 w-3.5" />
                Trigger First Evaluation
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {runs.map((run) => {
                const targetAsset = assets.find((a) => a.id === run.asset_id);
                const isReviewed = Boolean(run.reviewed_by);
                const summary = run.team_summary || {};
                const execSummary = (summary.executive_summary as string) || "Assessment in progress...";

                return (
                  <Link
                    key={run.id}
                    href={`/security-team/${run.id}`}
                    className="group p-5 rounded-lg bg-background-secondary border border-border-subtle hover:border-crimson/50 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
                  >
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2.5">
                        {getStatusBadge(run.status)}
                        {isReviewed ? (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950/60 border border-emerald-700 text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" /> HUMAN REVIEWED
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-amber-950/60 border border-amber-700 text-amber-300 flex items-center gap-1">
                            <Clock className="h-3 w-3" /> REVIEW REQUIRED
                          </span>
                        )}
                        <span className="text-xs font-mono text-neutral-400">
                          {run.orchestration_version}
                        </span>
                        <span className="text-xs text-neutral-500 font-mono">
                          • {new Date(run.created_at).toLocaleString()}
                        </span>
                      </div>

                      <div>
                        <h3 className="text-base font-semibold text-white group-hover:text-crimson-light transition-colors">
                          {targetAsset ? targetAsset.name : "Target Asset Perimeter"}
                        </h3>
                        <p className="text-xs text-neutral-400 line-clamp-2 mt-1">
                          {execSummary}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-neutral-400 pt-1">
                        <span>Confidence: <strong className="text-neutral-200">{(run.confidence * 100).toFixed(0)}%</strong></span>
                        {run.scan_id && <span>Scan Scope: <strong className="text-neutral-200">{run.scan_id.slice(0, 8)}</strong></span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 text-xs font-mono text-crimson group-hover:translate-x-1 transition-transform self-end md:self-center">
                      <span>View Team Assessment</span>
                      <ArrowRight className="h-4 w-4" />
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Trigger Evaluation Modal */}
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg rounded-xl bg-background-secondary border border-border-subtle p-6 space-y-5 shadow-2xl">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Play className="h-5 w-5 text-crimson" />
                  Trigger AI Security Team Evaluation
                </h3>
                <p className="text-xs text-neutral-400 mt-1">
                  Executes the 5-agent sequential orchestration over authorized scanner facts.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                    Target Authorized Asset
                  </label>
                  <select
                    value={selectedAssetId}
                    onChange={(e) => setSelectedAssetId(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-neutral-900 border border-neutral-700 text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                  >
                    {assets.map((asset) => (
                      <option key={asset.id} value={asset.id}>
                        {asset.name} ({asset.type} • {asset.criticality})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                    Filter by Scan (Optional)
                  </label>
                  <select
                    value={selectedScanId}
                    onChange={(e) => setSelectedScanId(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-neutral-900 border border-neutral-700 text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                  >
                    <option value="">All Scans for Asset</option>
                    {scans
                      .filter((s) => !selectedAssetId || s.asset_id === selectedAssetId)
                      .map((scan) => (
                        <option key={scan.id} value={scan.id}>
                          Scan {scan.id.slice(0, 8)} • {scan.scan_type} ({scan.status})
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-border-subtle">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  disabled={triggering}
                  className="px-4 py-2 rounded border border-neutral-700 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleTriggerRun}
                  disabled={triggering || !selectedAssetId}
                  className="px-4 py-2 rounded bg-crimson hover:bg-crimson/90 text-white text-xs font-medium flex items-center gap-2 disabled:opacity-50"
                >
                  {triggering ? <RotateCw className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  {triggering ? "Orchestrating Agents..." : "Start Evaluation"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </CommandCenterShell>
  );
}
