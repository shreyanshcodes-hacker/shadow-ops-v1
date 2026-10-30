"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { useAuth } from "@/context/AuthContext";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import {
  Asset,
  AttackPath,
  SecurityTeamRun,
  DashboardMetricsResponse,
  DashboardTrendsResponse,
} from "@/types";
import {
  ShieldCheck,
  Server,
  AlertTriangle,
  Activity,
  ArrowUpRight,
  Lock,
  Plus,
  Building2,
  Sliders,
  Users,
  Bot,
  Clock,
  CheckCircle2,
  FileText,
  TrendingUp,
  FileCheck,
  Terminal,
  RefreshCw,
} from "lucide-react";
import { AddAssetModal } from "@/components/assets/AddAssetModal";

export default function DashboardPage() {
  const { profile } = useAuth();
  const { activeWorkspace, workspaces, loadingWorkspaces } = useWorkspace();

  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null);
  const [trends, setTrends] = useState<DashboardTrendsResponse | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [attackPaths, setAttackPaths] = useState<AttackPath[]>([]);
  const [teamRuns, setTeamRuns] = useState<SecurityTeamRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    if (!activeWorkspace) {
      setMetrics(null);
      setTrends(null);
      setAssets([]);
      setAttackPaths([]);
      setTeamRuns([]);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const [metricData, trendData, assetData, pathData, teamData] = await Promise.all([
          apiClient.get<DashboardMetricsResponse>(`/reports/dashboard?workspace_id=${activeWorkspace.id}`).catch(() => null),
          apiClient.get<DashboardTrendsResponse>(`/reports/dashboard/trends?workspace_id=${activeWorkspace.id}&days=30`).catch(() => null),
          apiClient.get<Asset[]>(`/workspaces/${activeWorkspace.id}/assets`).catch(() => []),
          apiClient.get<AttackPath[]>(`/attack-paths?workspace_id=${activeWorkspace.id}`).catch(() => []),
          apiClient.get<SecurityTeamRun[]>(`/security-team/runs?workspace_id=${activeWorkspace.id}`).catch(() => []),
        ]);

        setMetrics(metricData);
        setTrends(trendData);
        setAssets(assetData || []);
        setAttackPaths(pathData || []);
        setTeamRuns(teamData || []);
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [activeWorkspace]);

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-7xl mx-auto pb-12">
          {/* Top Banner Alert regarding Security Boundary */}
          <Alert variant="info" title="AUTONOMOUS SECURITY BOUNDARY ENFORCED">
            Active Workspace:{" "}
            <span className="font-mono font-semibold text-white">
              {activeWorkspace?.name || "None Selected"}
            </span>
            . Security rule enforced by backend:{" "}
            <span className="font-mono font-semibold text-crimson-light">
              NO AUTHORIZATION → NO SCAN
            </span>
            .
          </Alert>

          {/* Missing Data Invariant Callout */}
          {activeWorkspace && metrics && !metrics.has_completed_scans && (
            <Alert variant="warning" title="INCOMPLETE PERIMETER DATA // ZERO COMPLETED SCANS">
              {metrics.data_disclaimer}
              <div className="mt-2 text-xs font-mono">
                Run an authorized scan on your repositories to establish a baseline vulnerability inventory.
              </div>
            </Alert>
          )}

          {/* Empty Workspace State */}
          {!loadingWorkspaces && workspaces.length === 0 && (
            <EmptyState
              icon={<Building2 className="h-6 w-6 text-crimson" />}
              title="No Security Workspaces Established"
              description="Create your first isolated multi-tenant perimeter to register repositories, configure access roles, and begin security operations."
            />
          )}

          {activeWorkspace && (
            <>
              {/* Executive Action Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border-subtle pb-4">
                <div>
                  <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary-light" />
                    Executive Security Posture
                  </h2>
                  <p className="text-xs text-neutral-400 font-mono">
                    Deterministic risk metrics, verification status, and audit-ready snapshots
                  </p>
                </div>

                <div className="flex items-center gap-2.5">
                  <Link href="/reports">
                    <Button variant="outline" size="sm" className="gap-1.5 text-xs font-mono">
                      <FileText className="h-3.5 w-3.5" />
                      Reports Archive
                    </Button>
                  </Link>

                  <Link href="/reports/new">
                    <Button variant="primary" size="sm" className="gap-1.5 text-xs">
                      <Plus className="h-3.5 w-3.5" />
                      Generate Report
                    </Button>
                  </Link>
                </div>
              </div>

              {/* Authoritative Metrics Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* 1. Deterministic Risk Score */}
                <Card className="bg-background-secondary border-border-subtle">
                  <CardContent className="p-4 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono text-neutral-400">
                      <span>DETERMINISTIC RISK</span>
                      <Activity className="h-4 w-4 text-emerald-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-mono text-white">
                        {metrics?.risk?.current_score !== null && metrics?.risk?.current_score !== undefined
                          ? metrics.risk.current_score.toFixed(1)
                          : "--"}
                      </span>
                      <Badge
                        variant={
                          metrics?.risk?.risk_band === "CRITICAL"
                            ? "critical"
                            : metrics?.risk?.risk_band === "HIGH"
                            ? "high"
                            : "default"
                        }
                      >
                        {metrics?.risk?.risk_band || (metrics?.has_completed_scans ? "LOW" : "UNSCANNED")}
                      </Badge>
                    </div>
                    <p className="text-[11px] font-mono text-neutral-500">
                      Model: {metrics?.risk?.formula_version || "risk-v1"} • 0–100 Engine
                    </p>
                  </CardContent>
                </Card>

                {/* 2. Open Vulnerabilities */}
                <Card className="bg-background-secondary border-border-subtle">
                  <CardContent className="p-4 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono text-neutral-400">
                      <span>OPEN VULNERABILITIES</span>
                      <AlertTriangle className="h-4 w-4 text-crimson" />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-mono text-crimson-light">
                        {metrics ? metrics.findings.open : 0}
                      </span>
                      <span className="text-xs text-neutral-400 font-mono">
                        ({metrics ? metrics.findings.fixed : 0} fixed)
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-mono text-neutral-400 pt-0.5">
                      <span className="text-crimson font-bold">
                        Crit: {metrics?.findings?.by_severity?.critical ?? 0}
                      </span>
                      <span>•</span>
                      <span className="text-amber-400 font-bold">
                        High: {metrics?.findings?.by_severity?.high ?? 0}
                      </span>
                      <span>•</span>
                      <span>Med: {metrics?.findings?.by_severity?.medium ?? 0}</span>
                    </div>
                  </CardContent>
                </Card>

                {/* 3. Attack Path Intelligence */}
                <Card className="bg-background-secondary border-border-subtle">
                  <CardContent className="p-4 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono text-neutral-400">
                      <span>ATTACK PATHS</span>
                      <Sliders className="h-4 w-4 text-amber-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-mono text-amber-400">
                        {attackPaths.length}
                      </span>
                      <span className="text-xs text-neutral-400 font-mono">active chains</span>
                    </div>
                    <p className="text-[11px] font-mono text-neutral-400">
                      {metrics?.risk?.critical_attack_paths_count ?? 0} critical lateral paths
                    </p>
                  </CardContent>
                </Card>

                {/* 4. Fix Verification & Remediation */}
                <Card className="bg-background-secondary border-border-subtle">
                  <CardContent className="p-4 space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-mono text-neutral-400">
                      <span>VERIFIED FIXES</span>
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold font-mono text-emerald-400">
                        {metrics ? metrics.verifications.verified_candidates : 0}
                      </span>
                      <span className="text-xs text-neutral-400 font-mono">
                        candidates
                      </span>
                    </div>
                    <p className="text-[11px] font-mono text-neutral-400">
                      {metrics ? metrics.remediations.applied : 0} patches applied • {metrics ? metrics.verifications.human_accepted : 0} signed-off
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* 30-Day Trends Trajectory Preview */}
              {trends && trends.data_available && (
                <Card className="bg-background-secondary border-border-subtle">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-primary-light" />
                        30-Day Security Posture Trajectory
                      </CardTitle>
                      <span className="text-[11px] font-mono text-neutral-500">
                        Window: 30 days ({trends.findings_trend.length} points)
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                      {/* Findings Velocity Box */}
                      <div className="p-3 bg-neutral-900/60 rounded border border-neutral-800 space-y-1">
                        <span className="text-[11px] font-mono text-neutral-400 block">Findings Velocity</span>
                        <div className="text-sm font-mono font-semibold text-white">
                          Open: {metrics?.findings?.open ?? 0} | Fixed: {metrics?.findings?.fixed ?? 0}
                        </div>
                        <p className="text-[10px] text-neutral-500 font-mono">
                          Tracking new vs resolved flaws daily
                        </p>
                      </div>

                      {/* Deterministic Risk History Box */}
                      <div className="p-3 bg-neutral-900/60 rounded border border-neutral-800 space-y-1">
                        <span className="text-[11px] font-mono text-neutral-400 block">Risk Score Trajectory</span>
                        <div className="text-sm font-mono font-semibold text-white">
                          Current: {metrics?.risk?.current_score !== null ? `${metrics?.risk?.current_score?.toFixed(1)}/100` : "N/A"}
                        </div>
                        <p className="text-[10px] text-neutral-500 font-mono">
                          Formula: {metrics?.risk?.formula_version || "risk-v1"}
                        </p>
                      </div>

                      {/* Remediation Flow Box */}
                      <div className="p-3 bg-neutral-900/60 rounded border border-neutral-800 space-y-1">
                        <span className="text-[11px] font-mono text-neutral-400 block">Remediation Velocity</span>
                        <div className="text-sm font-mono font-semibold text-white">
                          {metrics?.remediations?.applied ?? 0} Applied | {metrics?.verifications?.verified_candidates ?? 0} Verified
                        </div>
                        <p className="text-[10px] text-neutral-500 font-mono">
                          Safe patch lifecycle enforcement
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Assets & AI Team Section */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* AI Security Team */}
                <Card variant="bordered">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-sm font-mono flex items-center gap-2">
                          <Bot className="h-4 w-4 text-crimson" />
                          AI SECURITY TEAM ({teamRuns.length})
                        </CardTitle>
                        <CardDescription>
                          Collaborative 5-agent assessments requiring human review.
                        </CardDescription>
                      </div>
                      <Link href="/security-team">
                        <Button variant="outline" size="sm" className="text-xs">
                          Team Center
                        </Button>
                      </Link>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {teamRuns.length === 0 ? (
                      <div className="text-center py-6">
                        <p className="text-xs text-neutral-400 mb-2">
                          No AI Security Team evaluations triggered yet.
                        </p>
                        <Link href="/security-team">
                          <Button variant="primary" size="sm" className="text-xs">
                            Trigger Evaluation
                          </Button>
                        </Link>
                      </div>
                    ) : (
                      <div className="divide-y divide-border-subtle">
                        {teamRuns.slice(0, 3).map((run) => (
                          <Link
                            key={run.id}
                            href={`/security-team/${run.id}`}
                            className="py-2.5 flex items-center justify-between hover:bg-neutral-800/30 px-2 rounded transition-colors"
                          >
                            <div className="space-y-0.5">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono font-semibold text-white">
                                  Run #{run.id.slice(0, 8)}
                                </span>
                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-800 border border-neutral-700 text-neutral-300">
                                  {run.status}
                                </span>
                              </div>
                              <p className="text-[11px] text-neutral-400 font-mono">
                                Confidence: {(run.confidence * 100).toFixed(0)}% • {new Date(run.created_at).toLocaleDateString()}
                              </p>
                            </div>
                            <div className="text-right">
                              {run.reviewed_by ? (
                                <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1 justify-end">
                                  <CheckCircle2 className="h-3 w-3" /> REVIEWED
                                </span>
                              ) : (
                                <span className="text-[10px] font-mono text-amber-300 flex items-center gap-1 justify-end">
                                  <Clock className="h-3 w-3" /> REVIEW REQ
                                </span>
                              )}
                            </div>
                          </Link>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Perimeter Assets */}
                <Card variant="bordered">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-sm font-mono flex items-center gap-2">
                          <Server className="h-4 w-4 text-primary-light" />
                          PERIMETER ASSETS ({assets.length})
                        </CardTitle>
                        <CardDescription>
                          Targets registered in {activeWorkspace.name}.
                        </CardDescription>
                      </div>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setShowAddModal(true)}
                      >
                        <Plus className="h-4 w-4" />
                        Add Asset
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {assets.length === 0 ? (
                      <div className="text-center py-6">
                        <p className="text-xs text-neutral-400 mb-3">
                          No targets registered in this workspace yet.
                        </p>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setShowAddModal(true)}
                        >
                          Onboard First Repository
                        </Button>
                      </div>
                    ) : (
                      <div className="divide-y divide-border-subtle">
                        {assets.slice(0, 4).map((asset) => (
                          <div
                            key={asset.id}
                            className="py-2.5 flex items-center justify-between first:pt-0 last:pb-0"
                          >
                            <div className="flex flex-col space-y-0.5">
                              <span className="text-sm font-medium text-white">
                                {asset.name}
                              </span>
                              <span className="text-[11px] font-mono text-neutral-400">
                                {asset.type.toUpperCase()} • {asset.criticality.toUpperCase()}
                              </span>
                            </div>
                            <Badge
                              variant={
                                asset.authorization_status === "authorized" || asset.authorization_status === "verified"
                                  ? "success"
                                  : "high"
                              }
                            >
                              {(asset.authorization_status || "pending").toUpperCase()}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Attack Path Preview */}
              <Card variant="bordered">
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle className="text-sm font-mono flex items-center gap-2">
                      <Sliders className="h-4 w-4 text-crimson" />
                      <span>ATTACK PATH INTELLIGENCE ({attackPaths.length})</span>
                    </CardTitle>
                    <CardDescription>
                      Synthesized exploit chains and deterministic risk scoring (Model: risk-v1).
                    </CardDescription>
                  </div>
                  <Link
                    href="/attack-paths"
                    className="inline-flex items-center gap-1.5 text-xs text-crimson-light hover:underline font-mono"
                  >
                    All Attack Paths <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                </CardHeader>
                <CardContent>
                  {attackPaths.length === 0 ? (
                    <div className="py-6 text-center text-xs text-neutral-400 font-mono">
                      No attack paths currently synthesized. Discovered security relationships will assemble into paths automatically.
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      {attackPaths.slice(0, 3).map((path) => (
                        <Link
                          key={path.id}
                          href={`/attack-paths/${path.id}`}
                          className="flex items-center justify-between p-3 rounded bg-neutral-900 border border-neutral-800 hover:border-neutral-700 transition-colors"
                        >
                          <div className="space-y-1">
                            <div className="text-xs font-semibold text-white">
                              {path.title || path.name}
                            </div>
                            <div className="text-[11px] text-neutral-400 flex items-center gap-2 font-mono">
                              <span>Entry: {path.entry_point || "External"}</span>
                              <span>&bull;</span>
                              <span>{path.node_count} nodes</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            <span
                              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                                path.risk_band === "CRITICAL"
                                  ? "bg-crimson/20 text-crimson-light border-crimson/40"
                                  : path.risk_band === "HIGH"
                                  ? "bg-amber-950/40 text-amber-300 border-amber-600/40"
                                  : "bg-neutral-800 text-neutral-300 border-neutral-700"
                              }`}
                            >
                              {path.risk_band || "CALCULATING"} ({path.risk_score?.toFixed(1) ?? "--"})
                            </span>
                            <ArrowUpRight className="h-4 w-4 text-neutral-400" />
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}

          {/* Add Asset Modal */}
          {activeWorkspace && (
            <AddAssetModal
              isOpen={showAddModal}
              onClose={() => setShowAddModal(false)}
              workspaceId={activeWorkspace.id}
              onAssetCreated={(newAsset) => setAssets((prev) => [newAsset, ...prev])}
            />
          )}
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
