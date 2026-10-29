"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient, downloadFile } from "@/lib/api-client";
import { SecurityReport } from "@/types";
import {
  FileText,
  ArrowLeft,
  Download,
  ShieldCheck,
  AlertTriangle,
  Sparkles,
  Lock,
  CheckCircle2,
  ExternalLink,
  Code2,
  GitCommit,
  Layers,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params?.id as string;
  const { activeWorkspace } = useWorkspace();

  const [report, setReport] = useState<SecurityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    if (!activeWorkspace || !reportId) return;

    setLoading(true);
    setError(null);

    apiClient
      .get<SecurityReport>(`/reports/${reportId}?workspace_id=${activeWorkspace.id}`)
      .then((data) => setReport(data))
      .catch((err) => {
        console.error("Failed to load report snapshot:", err);
        setError(err?.error?.message || err?.message || "Failed to load security report.");
      })
      .finally(() => setLoading(false));
  }, [activeWorkspace, reportId]);

  const handleDownload = async (fmt: "pdf" | "json") => {
    if (!activeWorkspace || !reportId) return;
    setDownloadingFormat(fmt);
    try {
      await downloadFile(
        `/reports/${reportId}/download?workspace_id=${activeWorkspace.id}&format=${fmt}`
      );
    } catch (err) {
      console.error(`Download failed:`, err);
      alert(`Download failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <CommandCenterShell>
          <div className="p-12 text-center text-sm font-mono text-neutral-400">
            Loading frozen security report snapshot...
          </div>
        </CommandCenterShell>
      </ProtectedRoute>
    );
  }

  if (error || !report) {
    return (
      <ProtectedRoute>
        <CommandCenterShell>
          <div className="space-y-4 max-w-4xl mx-auto">
            <Alert variant="error" title="Report Not Found">
              {error || "The requested report snapshot does not exist or access is unauthorized."}
            </Alert>
            <Link href="/reports">
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Back to Reports Archive
              </Button>
            </Link>
          </div>
        </CommandCenterShell>
      </ProtectedRoute>
    );
  }

  const snap = report.snapshot_data || {};
  const metrics = snap.metrics;
  const execNarrative = snap.executive_narrative;

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-6xl mx-auto pb-12">
          {/* Top Breadcrumb & Action Bar */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border-subtle pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-mono text-neutral-400">
                <Link href="/reports" className="hover:text-white flex items-center gap-1">
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Reports Archive
                </Link>
                <span>/</span>
                <span className="text-neutral-300 truncate max-w-xs">{report.title}</span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2.5">
                <FileText className="h-5 w-5 text-primary-light" />
                {report.title}
              </h1>
            </div>

            <div className="flex items-center gap-2.5">
              <Button
                variant="primary"
                size="sm"
                disabled={downloadingFormat === "pdf"}
                onClick={() => handleDownload("pdf")}
                className="gap-2 text-xs"
              >
                <Download className="h-4 w-4" />
                {downloadingFormat === "pdf" ? "Exporting PDF..." : "Export PDF"}
              </Button>

              <Button
                variant="outline"
                size="sm"
                disabled={downloadingFormat === "json"}
                onClick={() => handleDownload("json")}
                className="gap-2 text-xs font-mono"
              >
                <Download className="h-4 w-4" />
                {downloadingFormat === "json" ? "Exporting..." : "Export JSON"}
              </Button>
            </div>
          </div>

          {/* Metadata Banner */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-background-secondary p-3.5 rounded border border-border-subtle text-xs font-mono">
            <div>
              <span className="text-neutral-500 block">Report Category</span>
              <span className="font-semibold text-white uppercase">{report.report_type.replace(/_/g, " ")}</span>
            </div>
            <div>
              <span className="text-neutral-500 block">Data Cutoff (UTC)</span>
              <span className="font-semibold text-white">
                {new Date(report.data_cutoff_at).toLocaleString("en-US", { timeZone: "UTC" })}
              </span>
            </div>
            <div>
              <span className="text-neutral-500 block">Completeness Status</span>
              <Badge variant={report.completeness_status === "COMPLETE" ? "success" : "high"}>
                {report.completeness_status}
              </Badge>
            </div>
            <div>
              <span className="text-neutral-500 block">Report ID</span>
              <span className="text-neutral-400 truncate block" title={report.id}>
                {report.id.slice(0, 13)}...
              </span>
            </div>
          </div>

          {/* Invariant & Confidentiality Notice */}
          <Alert variant="info" title="CONFIDENTIAL // DETERMINISTIC SECURITY AUDIT">
            This document represents a frozen, immutable snapshot for authorized personnel.
            All numerical metrics and risk scores are derived strictly from deterministic scan facts.
            Code snippets and logs have been sanitized with automated secret redaction.
          </Alert>

          {/* Section 1: Executive Metrics Cards (if available) */}
          {metrics && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="bg-background-secondary border-border-subtle">
                <CardContent className="p-4 space-y-1">
                  <div className="text-[11px] font-mono text-neutral-400">Deterministic Risk Score</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-bold font-mono text-white">
                      {metrics.risk_score !== null ? metrics.risk_score.toFixed(1) : "N/A"}
                    </span>
                    <Badge variant={metrics.risk_band === "CRITICAL" ? "critical" : "high"}>
                      {metrics.risk_band || "NOT CALCULATED"}
                    </Badge>
                  </div>
                  <div className="text-[10px] font-mono text-neutral-500">
                    Formula: {metrics.formula_version || "risk-v1"}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-background-secondary border-border-subtle">
                <CardContent className="p-4 space-y-1">
                  <div className="text-[11px] font-mono text-neutral-400">Open Vulnerabilities</div>
                  <div className="text-2xl font-bold font-mono text-crimson-light">
                    {metrics.open_findings_count ?? 0}
                  </div>
                  <div className="text-[10px] font-mono text-neutral-400">
                    Crit: {metrics.by_severity?.critical ?? 0} | High: {metrics.by_severity?.high ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-background-secondary border-border-subtle">
                <CardContent className="p-4 space-y-1">
                  <div className="text-[11px] font-mono text-neutral-400">Critical Attack Paths</div>
                  <div className="text-2xl font-bold font-mono text-amber-400">
                    {metrics.critical_attack_paths_count ?? 0}
                  </div>
                  <div className="text-[10px] font-mono text-neutral-500">
                    Active Paths: {metrics.active_attack_paths_count ?? 0}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-background-secondary border-border-subtle">
                <CardContent className="p-4 space-y-1">
                  <div className="text-[11px] font-mono text-neutral-400">Verified Fixes</div>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    {metrics.verifications_completed ?? 0}
                  </div>
                  <div className="text-[10px] font-mono text-neutral-500">
                    Applied Patches: {metrics.remediations_applied ?? 0}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Section 2: Executive Advisory Summary */}
          {execNarrative && (
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-amber-400" />
                    Executive Advisory Summary
                  </span>
                  <Badge variant={execNarrative.is_ai_generated ? "info" : "default"}>
                    {execNarrative.is_ai_generated ? "AI-ASSISTED ADVISORY" : "DETERMINISTIC SUMMARY"}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs leading-relaxed text-neutral-300">
                <div className="bg-neutral-900/60 p-4 rounded border border-neutral-800 whitespace-pre-line font-sans">
                  {execNarrative.narrative}
                </div>
                <div className="text-[11px] font-mono text-neutral-500 italic">
                  Note: {execNarrative.disclaimer}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Section 3: Specialized Content by Report Type */}

          {/* A. Executive Summary: Top Critical Findings & Attack Paths */}
          {report.report_type === "executive_summary" && (
            <div className="space-y-6">
              {snap.top_critical_findings && snap.top_critical_findings.length > 0 && (
                <Card className="bg-background-secondary border-border-subtle">
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-crimson" />
                      Priority Critical Findings ({snap.top_critical_findings.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs text-left">
                        <thead className="bg-neutral-900 text-neutral-400 font-mono text-[11px] border-b border-border-subtle">
                          <tr>
                            <th className="p-3">Severity</th>
                            <th className="p-3">Vulnerability / Rule</th>
                            <th className="p-3">Location</th>
                            <th className="p-3">CWE</th>
                            <th className="p-3">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border-subtle text-neutral-300">
                          {snap.top_critical_findings.map((f: any) => (
                            <tr key={f.finding_id} className="hover:bg-neutral-900/50">
                              <td className="p-3">
                                <Badge variant={f.severity === "critical" ? "critical" : "high"}>
                                  {f.severity.toUpperCase()}
                                </Badge>
                              </td>
                              <td className="p-3 font-semibold text-white">
                                {f.title}
                                <div className="text-[10px] font-mono text-neutral-500">{f.rule_id}</div>
                              </td>
                              <td className="p-3 font-mono text-[11px] text-neutral-400">
                                {f.file_path}:{f.line_start || 1}
                              </td>
                              <td className="p-3 font-mono text-neutral-400">{f.cwe_id || "N/A"}</td>
                              <td className="p-3">
                                <Badge variant="default">
                                  {f.status}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}

              {snap.attack_paths_summary && snap.attack_paths_summary.length > 0 && (
                <Card className="bg-background-secondary border-border-subtle">
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Layers className="h-4 w-4 text-amber-400" />
                      Critical Attack Paths ({snap.attack_paths_summary.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {snap.attack_paths_summary.map((ap: any) => (
                      <div key={ap.path_id} className="p-3 rounded bg-neutral-900/60 border border-neutral-800 flex items-center justify-between">
                        <div className="space-y-1">
                          <div className="font-semibold text-xs text-white flex items-center gap-2">
                            <Badge variant="critical">{ap.risk_tier}</Badge>
                            {ap.title}
                          </div>
                          <div className="text-[11px] font-mono text-neutral-400">
                            Target Asset: <span className="text-white">{ap.target_node}</span> | Steps: {ap.step_count}
                          </div>
                        </div>
                        <Badge variant="default">{ap.status.toUpperCase()}</Badge>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* B. Technical Vulnerability Report */}
          {report.report_type === "technical_vulnerability" && snap.findings && (
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>Detailed Technical Findings ({snap.findings.length})</span>
                  <Badge variant="default">Redaction Applied</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {snap.findings.map((f: any) => (
                  <div key={f.finding_id} className="p-4 rounded border border-border-subtle bg-neutral-900/40 space-y-3">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        <Badge variant={f.severity === "critical" ? "critical" : "high"}>
                          {f.severity.toUpperCase()}
                        </Badge>
                        <h4 className="font-bold text-sm text-white">{f.title}</h4>
                      </div>
                      <span className="text-[11px] font-mono text-neutral-400">
                        {f.file_path}:{f.line_start || 1}
                      </span>
                    </div>

                    <p className="text-xs text-neutral-300">{f.description}</p>

                    <div className="flex items-center gap-4 text-[11px] font-mono text-neutral-400 pt-1">
                      <span>Rule: {f.rule_id}</span>
                      <span>CWE: {f.cwe_id || "N/A"}</span>
                      <span>Asset: {f.asset_name}</span>
                    </div>

                    {f.evidence_items && f.evidence_items.length > 0 && (
                      <div className="mt-2 space-y-2">
                        <div className="text-[11px] font-mono text-neutral-400 flex items-center gap-1.5">
                          <Code2 className="h-3.5 w-3.5 text-primary-light" />
                          Sanitized Evidence Snippet:
                        </div>
                        <pre className="p-3 bg-neutral-950 border border-neutral-800 rounded font-mono text-[11px] text-neutral-300 overflow-x-auto whitespace-pre-wrap">
                          {f.evidence_items[0].snippet_redacted || "No content available."}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* C. Remediation Progress Report */}
          {report.report_type === "remediation_progress" && snap.proposals && (
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">
                  Remediation Proposals & Verification Status ({snap.proposals.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {snap.proposals.map((p: any) => (
                  <div key={p.proposal_id} className="p-4 rounded border border-border-subtle bg-neutral-900/40 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Badge variant={p.status === "applied" ? "success" : "high"}>
                          {p.status.toUpperCase()}
                        </Badge>
                        <h4 className="font-semibold text-xs text-white">{p.title}</h4>
                      </div>
                      <span className="text-[11px] font-mono text-neutral-400">
                        {p.applied_at ? `Applied: ${p.applied_at.slice(0, 10)}` : "Pending Application"}
                      </span>
                    </div>

                    <div className="text-xs text-neutral-300">{p.problem_summary}</div>

                    <div className="flex items-center gap-4 text-[11px] font-mono text-neutral-400 pt-1">
                      <span>Files: {(p.affected_files || []).join(", ") || "N/A"}</span>
                      {p.verification && (
                        <span className="text-emerald-400 font-semibold">
                          Verification: {p.verification.policy_verdict || p.verification.status}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* D. Fix Verification & Regression Report */}
          {report.report_type === "verification_regression" && snap.jobs && (
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>Independent Fix Verifications ({snap.jobs.length})</span>
                  <span className="text-xs font-mono text-neutral-400">
                    Rule: No sufficient evidence means no verified fix
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {snap.jobs.map((j: any) => (
                  <div key={j.job_id} className="p-4 rounded border border-border-subtle bg-neutral-900/40 space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2">
                        <Badge variant={j.status === "PASSED_PENDING_REVIEW" ? "success" : "high"}>
                          {j.status}
                        </Badge>
                        <Badge variant="info">
                          {j.policy_verdict || "VERDICT_PENDING"}
                        </Badge>
                      </div>
                      <span className="text-[11px] font-mono text-neutral-400">
                        Comparison: <strong className="text-white">{j.vulnerability_status || j.evidence_comparison_outcome || "N/A"}</strong>
                      </span>
                    </div>

                    {j.human_review && (
                      <div className="p-2.5 rounded bg-neutral-950/80 border border-neutral-800 text-xs space-y-1">
                        <div className="font-semibold text-white flex items-center gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                          Human Sign-Off: {j.human_review.decision?.toUpperCase()}
                        </div>
                        <p className="text-neutral-400 text-[11px]">
                          Rationale: {j.human_review.rationale || "Fix confirmed independently."}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* E. Asset Security Posture Report */}
          {report.report_type === "asset_security_posture" && snap.assets && (
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">
                  Monitored Digital Assets ({snap.assets.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-neutral-900 text-neutral-400 font-mono text-[11px] border-b border-border-subtle">
                      <tr>
                        <th className="p-3">Asset</th>
                        <th className="p-3">Type & Env</th>
                        <th className="p-3">Authorization</th>
                        <th className="p-3">Scan Health</th>
                        <th className="p-3">Open Vulnerabilities</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-subtle text-neutral-300">
                      {snap.assets.map((a: any) => (
                        <tr key={a.asset_id} className="hover:bg-neutral-900/50">
                          <td className="p-3 font-semibold text-white">
                            {a.name}
                            <div className="text-[10px] font-mono text-neutral-500">{a.target}</div>
                          </td>
                          <td className="p-3 font-mono text-[11px]">
                            {a.asset_type} ({a.environment})
                          </td>
                          <td className="p-3">
                            <Badge variant={a.authorization?.status === "authorized" || a.authorization?.status === "verified" ? "success" : "critical"}>
                              {(a.authorization?.status || "unauthorized").toUpperCase()}
                            </Badge>
                          </td>
                          <td className="p-3 font-mono text-[11px] text-neutral-400">
                            {a.scans?.latest_scan_status || "never_scanned"} ({a.scans?.total_runs || 0} runs)
                          </td>
                          <td className="p-3 font-mono text-white font-bold">
                            {a.open_findings_count ?? 0}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Collapsible Raw Snapshot JSON */}
          <div className="pt-4 border-t border-border-subtle">
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="flex items-center gap-2 text-xs font-mono text-neutral-400 hover:text-white transition-colors"
            >
              {showRawJson ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              {showRawJson ? "Hide Immutable Snapshot JSON" : "Inspect Immutable Snapshot JSON"}
            </button>

            {showRawJson && (
              <pre className="mt-3 p-4 bg-neutral-950 border border-neutral-800 rounded font-mono text-[11px] text-neutral-300 overflow-x-auto max-h-96">
                {JSON.stringify(report, null, 2)}
              </pre>
            )}
          </div>
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
