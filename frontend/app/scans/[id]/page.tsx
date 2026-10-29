"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { apiClient } from "@/lib/api-client";
import { Scan, ScanEvent, Finding, FindingAIAnalysis, ScanAnalysisSummaryResponse } from "@/types";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  FileCode,
  Sparkles,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Link as LinkIcon,
  Cpu,
} from "lucide-react";

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = params.id as string;

  const [scan, setScan] = useState<Scan | null>(null);
  const [events, setEvents] = useState<ScanEvent[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [aiAnalyses, setAiAnalyses] = useState<Record<string, FindingAIAnalysis>>({});
  const [loading, setLoading] = useState(true);
  const [analyzingAI, setAnalyzingAI] = useState(false);
  const [analyzingFindingId, setAnalyzingFindingId] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

  const fetchScanDetails = async () => {
    try {
      const [scanData, eventData, findingData] = await Promise.all([
        apiClient.get<Scan>(`/scans/${scanId}`),
        apiClient.get<ScanEvent[]>(`/scans/${scanId}/events`),
        apiClient.get<Finding[]>(`/scans/${scanId}/findings`),
      ]);
      setScan(scanData);
      setEvents(eventData);
      setFindings(findingData);

      // Fetch existing AI analyses for this scan
      try {
        const analyses = await apiClient.get<FindingAIAnalysis[]>(`/scans/${scanId}/ai-analysis`);
        const map: Record<string, FindingAIAnalysis> = {};
        for (const a of analyses) {
          map[a.finding_id] = a;
        }
        setAiAnalyses(map);
      } catch (err) {
        // Not analyzed yet or empty
      }
    } catch (err) {
      console.error("Failed to fetch scan details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScanDetails();
    const interval = setInterval(() => {
      if (scan && (scan.status === "queued" || scan.status === "running")) {
        fetchScanDetails();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [scanId, scan?.status]);

  const handleTriggerScanAIAnalysis = async () => {
    setAnalyzingAI(true);
    setAiError(null);
    try {
      const result = await apiClient.post<ScanAnalysisSummaryResponse>(`/scans/${scanId}/ai-analysis`, {
        force: true,
      });
      const map = { ...aiAnalyses };
      for (const a of result.analyses) {
        map[a.finding_id] = a;
      }
      setAiAnalyses(map);
    } catch (err: unknown) {
      console.error("Failed to run AI Security Manager:", err);
      setAiError("Failed to complete AI analysis. Check provider configuration or token budget.");
    } finally {
      setAnalyzingAI(false);
    }
  };

  const handleTriggerSingleFindingAI = async (findingId: string) => {
    setAnalyzingFindingId(findingId);
    setAiError(null);
    try {
      const result = await apiClient.post<FindingAIAnalysis>(`/findings/${findingId}/ai-analysis`);
      setAiAnalyses((prev) => ({
        ...prev,
        [findingId]: result,
      }));
    } catch (err: unknown) {
      console.error("Failed to analyze finding with AI:", err);
      setAiError("Failed to analyze finding. Please retry.");
    } finally {
      setAnalyzingFindingId(null);
    }
  };

  if (loading) {
    return (
      <ProtectedRoute>
        <CommandCenterShell>
          <div className="p-12 flex justify-center">
            <LoadingSpinner size="lg" />
          </div>
        </CommandCenterShell>
      </ProtectedRoute>
    );
  }

  if (!scan) {
    return (
      <ProtectedRoute>
        <CommandCenterShell>
          <div className="text-center py-12">
            <h2 className="text-lg font-semibold text-white">Scan Not Found</h2>
            <p className="text-xs text-neutral-400 mt-1">
              The requested scan record does not exist or you lack workspace membership.
            </p>
            <Link href="/scans" className="mt-4 inline-block">
              <Button variant="secondary" size="sm">
                Return to Scans
              </Button>
            </Link>
          </div>
        </CommandCenterShell>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* Top Bar Navigation */}
          <div className="flex items-center justify-between">
            <Link
              href="/scans"
              className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Scans</span>
            </Link>
            <div className="flex items-center gap-2">
              <Badge
                variant={
                  scan.status === "completed"
                    ? "success"
                    : scan.status === "running"
                    ? "medium"
                    : scan.status === "failed"
                    ? "critical"
                    : "default"
                }
              >
                {scan.status.toUpperCase()}
              </Badge>
              <span className="text-xs font-mono text-neutral-400">
                ID: {scan.id}
              </span>
            </div>
          </div>

          {/* Scan Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <span className="text-[10px] font-mono text-neutral-400 uppercase">
                ENGINE PROFILE
              </span>
              <div className="mt-2 text-base font-semibold text-white font-mono">
                {scan.scan_profile}
              </div>
              <p className="text-[11px] text-neutral-400 mt-1">
                Semgrep SAST Framework
              </p>
            </Card>

            <Card>
              <span className="text-[10px] font-mono text-neutral-400 uppercase">
                TOTAL FINDINGS
              </span>
              <div className="mt-2 text-2xl font-bold font-mono text-white">
                {scan.summary.total_findings}
              </div>
              <p className="text-[11px] text-neutral-400 mt-1">
                {scan.summary.critical} critical · {scan.summary.high} high
              </p>
            </Card>

            <Card>
              <span className="text-[10px] font-mono text-neutral-400 uppercase">
                AI ANALYSIS STATUS
              </span>
              <div className="mt-2 text-base font-semibold text-white font-mono flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-purple-400" />
                {Object.keys(aiAnalyses).length} / {findings.length} ENRICHED
              </div>
              <p className="text-[11px] text-neutral-400 mt-1">
                AI Security Manager (Advisory)
              </p>
            </Card>

            <Card>
              <span className="text-[10px] font-mono text-neutral-400 uppercase">
                ANALYSIS PROVENANCE
              </span>
              <div className="mt-2 text-xs font-semibold text-emerald-400 font-mono flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" />
                VERIFIED LEGAL CONSENT
              </div>
              <p className="text-[11px] text-neutral-400 mt-1">
                Enforced by backend gateway
              </p>
            </Card>
          </div>

          {/* Chronological Timeline */}
          <Card variant="bordered">
            <CardHeader>
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <Clock className="h-4 w-4 text-crimson" />
                <span>CHRONOLOGICAL EXECUTION TIMELINE</span>
              </CardTitle>
              <CardDescription>
                Deterministic log events emitted by the backend scanning worker.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 font-mono text-xs">
                {events.map((evt) => (
                  <div
                    key={evt.id}
                    className="flex items-start gap-3 border-l-2 border-border-muted pl-4 py-1"
                  >
                    <span className="text-[11px] text-neutral-500 whitespace-nowrap">
                      {new Date(evt.created_at).toLocaleTimeString()}
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      {evt.event_type}
                    </Badge>
                    <span className="text-neutral-300">{evt.message}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Vulnerability Findings and AI Security Manager Section */}
          <Card variant="bordered">
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <CardTitle className="text-sm font-mono flex items-center gap-2">
                    <FileCode className="h-4 w-4 text-crimson" />
                    <span>PARSED FINDINGS & AI ANALYSIS ({findings.length})</span>
                  </CardTitle>
                  <CardDescription>
                    Scanner findings paired with evidence-grounded AI Security Manager analysis.
                  </CardDescription>
                </div>
                {findings.length > 0 && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleTriggerScanAIAnalysis}
                      disabled={analyzingAI}
                      className="bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs flex items-center gap-1.5"
                    >
                      {analyzingAI ? (
                        <>
                          <LoadingSpinner size="sm" />
                          <span>ANALYZING WITH AI...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3.5 w-3.5" />
                          <span>RUN AI SECURITY MANAGER</span>
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {aiError && (
                <div className="mb-4 p-3 bg-red-950/40 border border-red-800/60 rounded text-red-300 text-xs flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
                  <span>{aiError}</span>
                </div>
              )}

              {findings.length === 0 ? (
                <div className="text-center py-8 text-neutral-400 text-xs">
                  No static analysis findings detected in target codebase.
                </div>
              ) : (
                <div className="space-y-6">
                  {findings.map((finding) => {
                    const ai = aiAnalyses[finding.id];
                    const isAnalyzingThis = analyzingFindingId === finding.id;

                    return (
                      <div
                        key={finding.id}
                        className="p-5 rounded-lg bg-background-tertiary/40 border border-border-subtle space-y-4"
                      >
                        {/* Finding Level 1/2 Header */}
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2.5">
                            <Badge
                              variant={
                                finding.severity === "critical"
                                  ? "critical"
                                  : finding.severity === "high"
                                  ? "high"
                                  : "medium"
                              }
                            >
                              {finding.severity.toUpperCase()}
                            </Badge>
                            <Link
                              href={`/findings/${finding.id}`}
                              className="text-sm font-semibold text-white hover:text-purple-300 transition-colors underline-offset-2 hover:underline"
                            >
                              {finding.title}
                            </Link>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-neutral-400">
                              {finding.source_rule_id}
                            </span>
                            {!ai && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleTriggerSingleFindingAI(finding.id)}
                                disabled={isAnalyzingThis || analyzingAI}
                                className="text-[11px] h-7 px-2 font-mono flex items-center gap-1 border-purple-800/60 text-purple-300 hover:bg-purple-950/30"
                              >
                                {isAnalyzingThis ? (
                                  <LoadingSpinner size="sm" />
                                ) : (
                                  <>
                                    <Sparkles className="h-3 w-3" />
                                    <span>AI Analyze</span>
                                  </>
                                )}
                              </Button>
                            )}
                          </div>
                        </div>

                        {/* Description */}
                        <p className="text-xs text-neutral-300 leading-relaxed">
                          {finding.description}
                        </p>

                        {/* File location & Code Snippet */}
                        {finding.code_snippet && (
                          <div className="space-y-1">
                            <div className="text-[10px] font-mono text-neutral-400">
                              Location: {finding.file_path}:{finding.line_start}
                            </div>
                            <pre className="p-2.5 rounded bg-background border border-border-subtle font-mono text-xs text-neutral-200 overflow-x-auto">
                              <code>{finding.code_snippet}</code>
                            </pre>
                          </div>
                        )}

                        {/* CWE Tags */}
                        {finding.cwe_ids && finding.cwe_ids.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {finding.cwe_ids.map((cwe) => (
                              <span
                                key={cwe}
                                className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-900 border border-neutral-700 text-neutral-400"
                              >
                                {cwe}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* AI Security Manager Analysis Card (Level 3 Advisory) */}
                        {ai && (
                          <div className="mt-4 p-4 rounded-md bg-purple-950/20 border border-purple-900/40 space-y-3">
                            <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-purple-900/30">
                              <div className="flex items-center gap-2">
                                <Sparkles className="h-4 w-4 text-purple-400" />
                                <span className="text-xs font-mono font-bold text-purple-200 uppercase tracking-wide">
                                  AI SECURITY MANAGER ANALYSIS (ADVISORY)
                                </span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-[11px] font-mono text-purple-300">
                                  Confidence: {Math.round(ai.confidence * 100)}%
                                </span>
                                <Badge variant="outline" className="text-[10px] border-purple-700 text-purple-300">
                                  {ai.classification}
                                </Badge>
                                <span className="text-[10px] font-mono text-neutral-500">
                                  {ai.provider.toUpperCase()} / {ai.model}
                                </span>
                              </div>
                            </div>

                            {/* Summary */}
                            <div>
                              <div className="text-[10px] font-mono uppercase text-purple-400">
                                Executive Summary
                              </div>
                              <p className="text-xs text-neutral-200 mt-0.5 leading-relaxed">
                                {ai.summary}
                              </p>
                            </div>

                            {/* Technical Explanation */}
                            <div>
                              <div className="text-[10px] font-mono uppercase text-purple-400">
                                Technical Explanation & Root Cause
                              </div>
                              <p className="text-xs text-neutral-300 mt-0.5 leading-relaxed">
                                {ai.technical_explanation}
                              </p>
                            </div>

                            {/* Impact */}
                            <div>
                              <div className="text-[10px] font-mono uppercase text-purple-400">
                                Operational & Business Impact
                              </div>
                              <p className="text-xs text-neutral-300 mt-0.5 leading-relaxed">
                                {ai.impact}
                              </p>
                            </div>

                            {/* Uncertainty */}
                            {ai.uncertainty && (
                              <div className="flex items-start gap-1.5 text-[11px] text-amber-300/90 bg-amber-950/20 p-2 rounded border border-amber-900/30">
                                <HelpCircle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-amber-400" />
                                <span><strong>Uncertainty / Context Notes:</strong> {ai.uncertainty}</span>
                              </div>
                            )}

                            {/* Grounded Evidence Items */}
                            {ai.supporting_evidence && ai.supporting_evidence.length > 0 && (
                              <div>
                                <div className="text-[10px] font-mono uppercase text-purple-400 flex items-center gap-1">
                                  <LinkIcon className="h-3 w-3" />
                                  <span>Grounded Supporting Evidence ({ai.supporting_evidence.length})</span>
                                </div>
                                <div className="mt-1 space-y-1.5">
                                  {ai.supporting_evidence.map((ev, i) => (
                                    <div
                                      key={i}
                                      className="text-[11px] p-2 bg-neutral-900/60 rounded border border-neutral-800 text-neutral-300"
                                    >
                                      <div className="font-mono text-[10px] text-neutral-400">
                                        Evidence ID: {ev.evidence_id}
                                      </div>
                                      <div className="mt-0.5">{ev.relevance}</div>
                                      {ev.quote_or_reference && (
                                        <div className="mt-1 text-[10px] font-mono text-purple-300">
                                          Ref: {ev.quote_or_reference}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Invariant Advisory Disclaimer */}
                            <div className="pt-2 border-t border-purple-900/30 flex items-center gap-1.5 text-[10px] text-neutral-400">
                              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                              <span>
                                Invariant Guarantee: AI analysis is advisory interpretation. Scanner findings, AST matches, and severity remain authoritative.
                              </span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
