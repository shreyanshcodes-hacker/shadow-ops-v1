"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { Finding, FindingAIAnalysis, SecurityRelationship, RemediationProposal } from "@/types";
import {
  ArrowLeft,
  FileCode,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  Eye,
  Brain,
  History,
  Link as LinkIcon,
  RefreshCw,
  GitBranch,
  Check,
  X,
  ExternalLink,
  Wrench,
} from "lucide-react";

export default function FindingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const findingId = params.id as string;
  const { activeWorkspace } = useWorkspace();

  const [finding, setFinding] = useState<Finding | null>(null);
  const [analyses, setAnalyses] = useState<FindingAIAnalysis[]>([]);
  const [relationships, setRelationships] = useState<SecurityRelationship[]>([]);
  const [selectedAnalysisIdx, setSelectedAnalysisIdx] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [correlating, setCorrelating] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [generatingRemediation, setGeneratingRemediation] = useState(false);
  const [verifying, setVerifying] = useState(false);

  const handleTriggerFindingVerification = async () => {
    const wsId = activeWorkspace?.id || (typeof window !== "undefined" ? localStorage.getItem("shadowops_active_workspace") : null);
    if (!wsId) {
      alert("No active workspace selected.");
      return;
    }
    setVerifying(true);
    try {
      const res = await apiClient.post<any>(
        `/findings/${findingId}/verify?workspace_id=${wsId}`
      );
      router.push(`/verifications/${res.id}`);
    } catch (err: any) {
      console.error("Failed to trigger verification:", err);
      alert(err?.message || "Failed to trigger fix verification.");
    } finally {
      setVerifying(false);
    }
  };

  const handleProposeRemediation = async () => {
    setGeneratingRemediation(true);
    try {
      const activeWs = typeof window !== "undefined"
        ? localStorage.getItem("shadowops_active_workspace") || "default"
        : "default";
      const proposal = await apiClient.post<RemediationProposal>(
        `/findings/${findingId}/remediations?workspace_id=${activeWs}`
      );
      router.push(`/remediations/${proposal.id}`);
    } catch (err) {
      console.error("Failed to generate remediation:", err);
      alert("Failed to generate remediation proposal. Verify active asset authorization.");
    } finally {
      setGeneratingRemediation(false);
    }
  };

  const fetchFindingData = async () => {
    try {
      const [findingData, aiData, relData] = await Promise.all([
        apiClient.get<Finding>(`/findings/${findingId}`),
        apiClient.get<FindingAIAnalysis[]>(`/findings/${findingId}/ai-analysis`).catch(() => []),
        apiClient.get<SecurityRelationship[]>(`/findings/${findingId}/relationships`).catch(() => []),
      ]);
      setFinding(findingData);
      setAnalyses(aiData);
      setRelationships(relData);
      setSelectedAnalysisIdx(0);
    } catch (err) {
      console.error("Failed to load finding details:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmRelationship = async (relId: string) => {
    try {
      await apiClient.post(`/relationships/${relId}/confirm`, {
        rationale: "Confirmed by security analyst in finding view",
      });
      const updatedRels = await apiClient.get<SecurityRelationship[]>(`/findings/${findingId}/relationships`);
      setRelationships(updatedRels);
    } catch (err) {
      console.error("Failed to confirm relationship:", err);
    }
  };

  const handleDismissRelationship = async (relId: string) => {
    try {
      await apiClient.post(`/relationships/${relId}/dismiss`, {
        rationale: "Dismissed by security analyst in finding view",
      });
      const updatedRels = await apiClient.get<SecurityRelationship[]>(`/findings/${findingId}/relationships`);
      setRelationships(updatedRels);
    } catch (err) {
      console.error("Failed to dismiss relationship:", err);
    }
  };

  const handleRunCorrelation = async () => {
    setCorrelating(true);
    try {
      await apiClient.post(`/findings/${findingId}/correlate?include_ai=true`);
      const updatedRels = await apiClient.get<SecurityRelationship[]>(`/findings/${findingId}/relationships`);
      setRelationships(updatedRels);
    } catch (err) {
      console.error("Failed to run correlation:", err);
    } finally {
      setCorrelating(false);
    }
  };

  useEffect(() => {
    fetchFindingData();
  }, [findingId]);

  const handleRunAnalysis = async (force = false, provider?: string) => {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const result = await apiClient.post<FindingAIAnalysis>(`/findings/${findingId}/ai-analysis`, {
        force,
        provider,
      });
      // Refresh historical analyses list
      const updatedAnalyses = await apiClient.get<FindingAIAnalysis[]>(`/findings/${findingId}/ai-analysis`);
      setAnalyses(updatedAnalyses);
      setSelectedAnalysisIdx(0);
    } catch (err: unknown) {
      console.error("AI Analysis failed:", err);
      setAnalysisError("AI Security Analyst request failed. Upstream provider unavailable or credentials missing.");
    } finally {
      setAnalyzing(false);
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

  if (!finding) {
    return (
      <ProtectedRoute>
        <CommandCenterShell>
          <div className="text-center py-12">
            <h2 className="text-lg font-semibold text-white">Finding Not Found</h2>
            <p className="text-xs text-neutral-400 mt-1">
              The requested finding does not exist or you lack workspace membership.
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

  const currentAnalysis = analyses[selectedAnalysisIdx] || null;

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* Header Navigation */}
          <div className="flex items-center justify-between">
            <Link
              href={`/scans/${finding.scan_id}`}
              className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              <span>Back to Scan Details</span>
            </Link>
            <div className="flex items-center gap-2">
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
              <span className="text-xs font-mono text-neutral-400">
                Finding ID: {finding.id}
              </span>
            </div>
          </div>

          {/* SECTION 1: AUTHORITATIVE SCANNER FACTS */}
          <Card variant="bordered">
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <FileCode className="h-4 w-4 text-crimson" />
                    <span className="text-xs font-mono text-crimson uppercase tracking-wider font-bold">
                      GROUND TRUTH (AUTHORITATIVE SCANNER FACTS)
                    </span>
                  </div>
                  <CardTitle className="text-base text-white mt-1">
                    {finding.title}
                  </CardTitle>
                  <CardDescription className="font-mono text-xs text-neutral-400 mt-0.5">
                    Engine: {finding.source.toUpperCase()} · Rule: {finding.source_rule_id}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs border-neutral-700 text-neutral-300">
                    Status: {finding.status.toUpperCase()}
                  </Badge>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={handleProposeRemediation}
                    disabled={generatingRemediation}
                    className="gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white font-mono"
                  >
                    <Wrench className="h-3.5 w-3.5" />
                    {generatingRemediation ? "Generating..." : "Generate AI Patch"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleTriggerFindingVerification}
                    disabled={verifying}
                    className="gap-1.5 text-xs border-emerald-500/40 text-emerald-400 hover:bg-emerald-950/30 font-mono"
                  >
                    <ShieldCheck className="h-3.5 w-3.5" />
                    {verifying ? "Verifying..." : "Verify Fix"}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-neutral-300 leading-relaxed">
                {finding.description}
              </p>

              {/* Code Location & Snippet */}
              {finding.code_snippet && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-mono text-neutral-400">
                    Target File: <span className="text-neutral-200">{finding.file_path || "Unknown"}</span>
                    {finding.line_start && ` · Lines: ${finding.line_start}-${finding.line_end || finding.line_start}`}
                  </div>
                  <pre className="p-3 rounded bg-background border border-border-subtle font-mono text-xs text-neutral-200 overflow-x-auto">
                    <code>{finding.code_snippet}</code>
                  </pre>
                </div>
              )}

              {/* Classification Badges */}
              <div className="flex flex-wrap gap-2 pt-2 border-t border-border-subtle">
                {finding.cwe_ids?.map((cwe) => (
                  <Badge key={cwe} variant="outline" className="font-mono text-[10px] text-neutral-300">
                    {cwe}
                  </Badge>
                ))}
                {finding.owasp_categories?.map((cat) => (
                  <Badge key={cat} variant="outline" className="font-mono text-[10px] text-neutral-400 border-neutral-800">
                    {cat}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* SECTION 2: AI SECURITY ANALYSIS (ADVISORY INTERPRETATION) */}
          <Card variant="bordered" className="border-purple-900/40 bg-purple-950/10">
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-purple-400" />
                    <span className="text-xs font-mono text-purple-300 uppercase tracking-wider font-bold">
                      AI SECURITY ANALYST (ADVISORY INTERPRETATION)
                    </span>
                  </div>
                  <CardTitle className="text-base text-white mt-1">
                    Structured Vulnerability Evaluation
                  </CardTitle>
                  <CardDescription className="text-xs text-purple-300/80">
                    Synthesizes code context and AST evidence into an actionable risk assessment for human review.
                  </CardDescription>
                </div>

                {/* Actions & Analysis History Switcher */}
                <div className="flex items-center gap-2 flex-wrap">
                  {analyses.length > 1 && (
                    <div className="flex items-center gap-1.5 text-xs font-mono text-neutral-400 bg-neutral-900/80 px-2 py-1 rounded border border-neutral-800">
                      <History className="h-3.5 w-3.5 text-purple-400" />
                      <span>Version:</span>
                      <select
                        value={selectedAnalysisIdx}
                        onChange={(e) => setSelectedAnalysisIdx(Number(e.target.value))}
                        className="bg-transparent text-white focus:outline-none cursor-pointer"
                      >
                        {analyses.map((a, idx) => (
                          <option key={a.id} value={idx} className="bg-neutral-900 text-white">
                            v{analyses.length - idx} · {a.provider.toUpperCase()} ({new Date(a.created_at).toLocaleTimeString()})
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleRunAnalysis(analyses.length > 0)}
                    disabled={analyzing}
                    className="bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs flex items-center gap-1.5"
                  >
                    {analyzing ? (
                      <>
                        <LoadingSpinner size="sm" />
                        <span>ANALYZING...</span>
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-3.5 w-3.5" />
                        <span>{analyses.length > 0 ? "RE-ANALYZE" : "ANALYZE WITH AI"}</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              {/* Error Notice */}
              {analysisError && (
                <div className="mb-4 p-3 bg-red-950/40 border border-red-800/60 rounded text-red-300 text-xs flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
                  <span>{analysisError}</span>
                </div>
              )}

              {/* State 1: NOT ANALYZED */}
              {!currentAnalysis && !analyzing && (
                <div className="text-center py-10 space-y-3">
                  <div className="mx-auto w-10 h-10 rounded-full bg-purple-900/30 flex items-center justify-center">
                    <Brain className="h-5 w-5 text-purple-400" />
                  </div>
                  <div className="text-sm font-semibold text-white">
                    No AI Security Analysis Generated Yet
                  </div>
                  <p className="text-xs text-neutral-400 max-w-md mx-auto">
                    Click &quot;Analyze with AI&quot; to invoke the AI Security Analyst on this finding. Evidence will be sanitized and analyzed safely.
                  </p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleRunAnalysis(false)}
                    className="mt-2 text-xs font-mono"
                  >
                    Run Security Analysis
                  </Button>
                </div>
              )}

              {/* State 2: ANALYZING */}
              {analyzing && (
                <div className="text-center py-12 space-y-3">
                  <LoadingSpinner size="lg" />
                  <div className="text-sm font-semibold text-white">
                    Analyzing Code Context & Grounded Evidence...
                  </div>
                  <p className="text-xs text-neutral-400 font-mono">
                    Redacting secrets · Constructing fenced prompt · Calling provider
                  </p>
                </div>
              )}

              {/* State 3: ANALYSIS AVAILABLE */}
              {currentAnalysis && !analyzing && (
                <div className="space-y-5">
                  {/* Metadata Header Pill */}
                  <div className="flex items-center justify-between flex-wrap gap-2 p-3 bg-neutral-900/60 rounded border border-neutral-800 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-purple-300 font-semibold">
                        Confidence: {Math.round(currentAnalysis.confidence * 100)}%
                      </span>
                      <Badge variant="outline" className="text-[10px] border-purple-700 text-purple-300">
                        {currentAnalysis.vulnerability_type || currentAnalysis.classification}
                      </Badge>
                      <Badge variant="outline" className="text-[10px] border-neutral-700 text-neutral-400">
                        Severity: {(currentAnalysis.severity_assessment || "advisory").toUpperCase()}
                      </Badge>
                    </div>
                    <div className="text-[10px] font-mono text-neutral-500">
                      {currentAnalysis.provider.toUpperCase()} / {currentAnalysis.model} · {currentAnalysis.prompt_version}
                    </div>
                  </div>

                  {/* Summary */}
                  <div>
                    <h4 className="text-xs font-mono uppercase text-purple-400 font-semibold">
                      Executive Summary
                    </h4>
                    <p className="text-xs text-neutral-200 mt-1 leading-relaxed">
                      {currentAnalysis.summary}
                    </p>
                  </div>

                  {/* Exploitability & Impact Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3.5 bg-neutral-900/40 rounded border border-neutral-800 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-neutral-400 font-semibold">
                        Exploitability Conditions
                      </span>
                      <p className="text-xs text-neutral-300 leading-relaxed">
                        {currentAnalysis.exploitability_assessment || "See technical reasoning below."}
                      </p>
                      {currentAnalysis.attack_preconditions && (
                        <div className="text-[11px] text-neutral-400 pt-1">
                          <strong>Preconditions:</strong> {currentAnalysis.attack_preconditions}
                        </div>
                      )}
                    </div>

                    <div className="p-3.5 bg-neutral-900/40 rounded border border-neutral-800 space-y-1">
                      <span className="text-[10px] font-mono uppercase text-neutral-400 font-semibold">
                        Potential Impact
                      </span>
                      <p className="text-xs text-neutral-300 leading-relaxed">
                        {currentAnalysis.impact_assessment || currentAnalysis.impact}
                      </p>
                      {currentAnalysis.affected_component && (
                        <div className="text-[11px] text-neutral-400 pt-1">
                          <strong>Affected Component:</strong> {currentAnalysis.affected_component}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* MANDATORY DISTINCTION: OBSERVED vs INFERRED vs UNCERTAIN */}
                  {currentAnalysis.evidence_interpretation && (
                    <div className="p-4 bg-neutral-950/70 rounded-md border border-neutral-800 space-y-3">
                      <div className="text-xs font-mono uppercase text-purple-300 font-bold tracking-wide">
                        EVIDENCE INTERPRETATION (OBSERVED · INFERRED · UNCERTAIN)
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {/* Observed */}
                        <div className="space-y-1.5 p-3 rounded bg-emerald-950/20 border border-emerald-900/40">
                          <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-emerald-400">
                            <Eye className="h-3.5 w-3.5" />
                            <span>OBSERVED FACTS</span>
                          </div>
                          <ul className="text-[11px] text-neutral-300 space-y-1 list-disc list-inside">
                            {currentAnalysis.evidence_interpretation.observed?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
                            )) || <li>Scanner pattern matched at target line span.</li>}
                          </ul>
                        </div>

                        {/* Inferred */}
                        <div className="space-y-1.5 p-3 rounded bg-purple-950/20 border border-purple-900/40">
                          <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-purple-400">
                            <Brain className="h-3.5 w-3.5" />
                            <span>INFERRED RISKS</span>
                          </div>
                          <ul className="text-[11px] text-neutral-300 space-y-1 list-disc list-inside">
                            {currentAnalysis.evidence_interpretation.inferred?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
                            )) || <li>Untrusted parameter execution potential.</li>}
                          </ul>
                        </div>

                        {/* Uncertain */}
                        <div className="space-y-1.5 p-3 rounded bg-amber-950/20 border border-amber-900/40">
                          <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-amber-400">
                            <HelpCircle className="h-3.5 w-3.5" />
                            <span>UNCERTAINTIES</span>
                          </div>
                          <ul className="text-[11px] text-neutral-300 space-y-1 list-disc list-inside">
                            {currentAnalysis.evidence_interpretation.uncertain?.map((item: string, i: number) => (
                              <li key={i}>{item}</li>
                            )) || <li>Dynamic input reachability requires runtime verification.</li>}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Technical Reasoning */}
                  <div>
                    <h4 className="text-xs font-mono uppercase text-purple-400 font-semibold">
                      Technical Reasoning & Mechanism
                    </h4>
                    <p className="text-xs text-neutral-300 mt-1 leading-relaxed">
                      {currentAnalysis.reasoning || currentAnalysis.technical_explanation}
                    </p>
                  </div>

                  {/* Recommended Next Steps */}
                  <div className="p-3.5 bg-neutral-900/50 rounded border border-neutral-800 space-y-1">
                    <span className="text-[10px] font-mono uppercase text-neutral-400 font-semibold">
                      Recommended Next Steps for Human Security Reviewer
                    </span>
                    <p className="text-xs text-neutral-200 leading-relaxed">
                      {currentAnalysis.recommended_next_steps || "Perform code inspection of caller sites to verify parameter validation."}
                    </p>
                  </div>

                  {/* Grounded Supporting Evidence */}
                  {currentAnalysis.supporting_evidence && currentAnalysis.supporting_evidence.length > 0 && (
                    <div>
                      <h4 className="text-xs font-mono uppercase text-purple-400 font-semibold flex items-center gap-1">
                        <LinkIcon className="h-3 w-3" />
                        <span>Grounded Supporting Evidence Citations ({currentAnalysis.supporting_evidence.length})</span>
                      </h4>
                      <div className="mt-1.5 space-y-1.5">
                        {currentAnalysis.supporting_evidence.map((ev, i) => (
                          <div
                            key={i}
                            className="p-2.5 bg-neutral-900/60 rounded border border-neutral-800 text-xs text-neutral-300"
                          >
                            <div className="font-mono text-[10px] text-neutral-400">
                              Evidence ID: {ev.evidence_id}
                            </div>
                            <div className="mt-0.5">{ev.relevance}</div>
                            {ev.quote_or_reference && (
                              <div className="mt-1 text-[10px] font-mono text-purple-300">
                                Reference: {ev.quote_or_reference}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Human-in-the-Loop Advisory Disclaimer */}
                  <div className="p-3 rounded bg-purple-950/30 border border-purple-900/50 flex items-center gap-2 text-xs text-neutral-300">
                    <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>
                      <strong>AI SECURITY ANALYSIS NOTICE:</strong> This analysis is AI-generated advisory interpretation and should be reviewed by a human security engineer. Scanner findings & severity remain authoritative.
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Security Relationships & Attack Path Correlation */}
          <Card className="border-border-subtle bg-background-secondary">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base text-white flex items-center gap-2">
                  <GitBranch className="h-4 w-4 text-amber-400" />
                  <span>Security Relationships & Attack Vectors</span>
                  <Badge variant="outline" className="font-mono text-[10px] text-amber-300 border-amber-800">
                    {relationships.length} Identified
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs text-neutral-400 mt-1">
                  Contextual connections discovered via deterministic code proximity and AI contextual reasoning.
                </CardDescription>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleRunCorrelation}
                  disabled={correlating}
                  className="text-xs gap-1.5 h-8 bg-neutral-900 border-neutral-700 hover:bg-neutral-800"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${correlating ? "animate-spin" : ""}`} />
                  {correlating ? "Correlating..." : "Discover Relationships"}
                </Button>
                <Link
                  href="/security-team"
                  className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-crimson/20 text-crimson-light border border-crimson/40 hover:bg-crimson/30 transition-colors font-medium"
                >
                  <Brain className="h-3.5 w-3.5" />
                  AI Security Team
                </Link>
                <Link
                  href="/attack-paths"
                  className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-amber-950/40 text-amber-300 border border-amber-800 hover:bg-amber-900/40 transition-colors font-medium"
                >
                  View Attack Paths <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </div>
            </CardHeader>

            <CardContent>
              {relationships.length === 0 ? (
                <div className="p-8 text-center bg-neutral-900/40 rounded border border-neutral-800">
                  <GitBranch className="h-8 w-8 text-neutral-400 mx-auto mb-2 opacity-50" />
                  <p className="text-xs text-neutral-400">
                    No active security relationships found for this finding yet.
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleRunCorrelation}
                    disabled={correlating}
                    className="mt-3 text-xs gap-1.5 border-neutral-700"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${correlating ? "animate-spin" : ""}`} />
                    Run Relationship Discovery
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {relationships.map((rel) => {
                    const isSource = rel.source_finding_id === finding.id;
                    return (
                      <div
                        key={rel.id}
                        className="p-3.5 rounded bg-neutral-900/70 border border-neutral-800 hover:border-neutral-700 transition-colors space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-amber-950/50 text-amber-300 border border-amber-800">
                              {rel.relationship_type}
                            </span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700 uppercase">
                              {rel.source}
                            </span>
                            <span className="text-[10px] font-mono text-neutral-400">
                              Confidence: {(rel.confidence * 100).toFixed(0)}%
                            </span>
                            <span
                              className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                                rel.status === "confirmed"
                                  ? "bg-emerald-950/40 text-emerald-300 border border-emerald-800"
                                  : rel.status === "dismissed"
                                  ? "bg-neutral-800 text-neutral-400 border border-neutral-700"
                                  : "bg-blue-950/40 text-blue-300 border border-blue-800"
                              }`}
                            >
                              {rel.status.toUpperCase()}
                            </span>
                          </div>

                          {rel.status === "active" && (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => handleConfirmRelationship(rel.id)}
                                title="Confirm this relationship"
                                className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono bg-emerald-950/40 text-emerald-300 border border-emerald-800 hover:bg-emerald-900/40 transition-colors"
                              >
                                <Check className="h-3 w-3" /> Confirm
                              </button>
                              <button
                                onClick={() => handleDismissRelationship(rel.id)}
                                title="Dismiss this relationship"
                                className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono bg-neutral-800 text-neutral-400 border border-neutral-700 hover:bg-neutral-700 transition-colors"
                              >
                                <X className="h-3 w-3" /> Dismiss
                              </button>
                            </div>
                          )}
                        </div>

                        <div className="text-xs text-neutral-200">
                          {isSource ? (
                            <span>
                              <strong>This Finding</strong> &rarr;{" "}
                              <Link
                                href={`/findings/${rel.target_finding_id}`}
                                className="text-crimson-light hover:underline font-medium"
                              >
                                {rel.target_finding_title || `Finding ${rel.target_finding_id.slice(0, 8)}...`}
                              </Link>
                            </span>
                          ) : (
                            <span>
                              <Link
                                href={`/findings/${rel.source_finding_id}`}
                                className="text-crimson-light hover:underline font-medium"
                              >
                                {rel.source_finding_title || `Finding ${rel.source_finding_id.slice(0, 8)}...`}
                              </Link>{" "}
                              &rarr; <strong>This Finding</strong>
                            </span>
                          )}
                        </div>

                        {rel.rationale && (
                          <p className="text-xs text-neutral-400 leading-relaxed font-sans bg-neutral-950/40 p-2 rounded border border-neutral-800/60">
                            {rel.rationale}
                          </p>
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
