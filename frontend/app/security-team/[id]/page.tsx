"use client";

import React, { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import {
  Shield,
  Bot,
  Users,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  RotateCw,
  Search,
  Sliders,
  Layers,
  FileCheck,
  ChevronDown,
  ChevronRight,
  XCircle,
  MessageSquare,
  Sparkles,
} from "lucide-react";

import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { SecurityTeamRunDetail, TeamAgentRun } from "@/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function SecurityTeamDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const runId = resolvedParams.id;

  const { activeWorkspace } = useWorkspace();
  const [detail, setDetail] = useState<SecurityTeamRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedAgent, setExpandedAgent] = useState<string | null>("security_reviewer");
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewNotes, setReviewNotes] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);
  const [canceling, setCanceling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!activeWorkspace) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<SecurityTeamRunDetail>(
        `/security-team/runs/${runId}?workspace_id=${activeWorkspace.id}`
      );
      setDetail(data);
    } catch (err: unknown) {
      console.error("Failed to load run details", err);
      setError("Unable to retrieve team run details.");
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace, runId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handleCancel = async () => {
    if (!activeWorkspace || !detail) return;
    try {
      setCanceling(true);
      const updated = await apiClient.post<SecurityTeamRunDetail>(
        `/security-team/runs/${runId}/cancel?workspace_id=${activeWorkspace.id}`
      );
      setDetail(updated);
    } catch (err: unknown) {
      console.error("Failed to cancel run", err);
      alert("Failed to cancel team run.");
    } finally {
      setCanceling(false);
    }
  };

  const handleReviewSubmit = async () => {
    if (!activeWorkspace || !detail) return;
    try {
      setSubmittingReview(true);
      const updated = await apiClient.post<SecurityTeamRunDetail>(
        `/security-team/runs/${runId}/review?workspace_id=${activeWorkspace.id}`,
        { notes: reviewNotes }
      );
      setDetail(updated);
      setShowReviewModal(false);
    } catch (err: unknown) {
      console.error("Failed to submit human review", err);
      alert("Failed to record human review.");
    } finally {
      setSubmittingReview(false);
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

  const assessment = detail?.assessment || (detail?.team_summary as unknown as SecurityTeamRunDetail["assessment"]);

  const getAgentIcon = (name: string) => {
    switch (name) {
      case "recon":
        return <Search className="h-4 w-4 text-cyan-400" />;
      case "vulnerability_analyst":
        return <AlertTriangle className="h-4 w-4 text-amber-400" />;
      case "attack_path":
        return <Sliders className="h-4 w-4 text-crimson-light" />;
      case "risk_analyst":
        return <Layers className="h-4 w-4 text-purple-400" />;
      case "security_reviewer":
        return <FileCheck className="h-4 w-4 text-emerald-400" />;
      default:
        return <Bot className="h-4 w-4 text-neutral-400" />;
    }
  };

  return (
    <CommandCenterShell>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2">
          <Link
            href="/security-team"
            className="text-xs font-mono text-neutral-400 hover:text-white flex items-center gap-1.5 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Security Team
          </Link>
          <span className="text-neutral-600">/</span>
          <span className="text-xs font-mono text-neutral-500">Run {runId.slice(0, 8)}</span>
        </div>

        {loading ? (
          <div className="p-16 text-center text-neutral-400 font-mono text-sm border border-border-subtle rounded-lg bg-background-secondary">
            <RotateCw className="h-6 w-6 animate-spin mx-auto mb-2 text-crimson" />
            Loading security team orchestration and agent outputs...
          </div>
        ) : error || !detail ? (
          <div className="p-6 rounded-lg bg-crimson/10 border border-crimson/30 text-crimson text-sm">
            {error || "Team run not found."}
          </div>
        ) : (
          <>
            {/* Top Header Card */}
            <div className="p-6 rounded-xl bg-background-secondary border border-border-subtle space-y-4">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2.5 mb-2">
                    {getStatusBadge(detail.status)}
                    <span className="text-xs font-mono text-neutral-400">
                      {detail.orchestration_version}
                    </span>
                    <span className="text-xs font-mono text-neutral-500">
                      • {new Date(detail.created_at).toLocaleString()}
                    </span>
                  </div>
                  <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <Users className="h-6 w-6 text-crimson" />
                    Security Team Assessment #{detail.id.slice(0, 8)}
                  </h1>
                </div>

                <div className="flex items-center gap-3">
                  {["QUEUED", "RUNNING"].includes(detail.status) && (
                    <button
                      onClick={handleCancel}
                      disabled={canceling}
                      className="px-3.5 py-1.5 rounded border border-neutral-700 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium flex items-center gap-1.5"
                    >
                      <XCircle className="h-4 w-4 text-neutral-400" />
                      {canceling ? "Canceling..." : "Cancel Run"}
                    </button>
                  )}

                  {!detail.reviewed_by ? (
                    <button
                      onClick={() => setShowReviewModal(true)}
                      className="px-4 py-2 rounded bg-crimson hover:bg-crimson/90 text-white text-xs font-medium flex items-center gap-2 shadow-lg shadow-crimson/20"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      Sign Off / Human Review
                    </button>
                  ) : (
                    <div className="px-3 py-1.5 rounded bg-emerald-950/60 border border-emerald-700 text-emerald-400 text-xs font-mono flex items-center gap-1.5">
                      <CheckCircle2 className="h-4 w-4" />
                      Human Reviewed on {detail.reviewed_at ? new Date(detail.reviewed_at).toLocaleDateString() : "Record"}
                    </div>
                  )}
                </div>
              </div>

              {/* Mandatory Human Review Banner */}
              <div className={`p-4 rounded-lg border flex flex-col md:flex-row md:items-center md:justify-between gap-3 ${
                detail.reviewed_by
                  ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-300"
                  : "bg-amber-950/30 border-amber-800/50 text-amber-200"
              }`}>
                <div className="flex items-start gap-3">
                  {detail.reviewed_by ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <Clock className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="text-xs font-bold font-mono uppercase tracking-wider">
                      {detail.reviewed_by
                        ? "Human Review Complete"
                        : "AI ANALYSIS COMPLETE — HUMAN REVIEW REQUIRED"}
                    </p>
                    <p className="text-xs text-neutral-400 mt-0.5">
                      {detail.reviewed_by
                        ? `Reviewed with notes: "${detail.review_notes || "Approved by security engineer."}"`
                        : "AI agents cannot approve changes, exploit targets, or mutate scanner facts. A qualified engineer must review and verify."}
                    </p>
                  </div>
                </div>

                <div className="text-xs font-mono text-neutral-400 shrink-0">
                  Confidence: <span className="font-bold text-white">{(detail.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>

            {/* Structured Executive Team Assessment */}
            {assessment && (
              <div className="p-6 rounded-xl bg-background-secondary border border-border-subtle space-y-6">
                <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
                  <Sparkles className="h-5 w-5 text-crimson" />
                  <h2 className="text-base font-semibold text-white">Executive Team Assessment</h2>
                </div>

                {/* Executive Summary */}
                <div className="space-y-1.5">
                  <h3 className="text-xs font-mono uppercase text-neutral-400">Executive Summary</h3>
                  <p className="text-sm text-neutral-200 bg-neutral-900/60 p-4 rounded-lg border border-neutral-800 leading-relaxed">
                    {assessment.executive_summary}
                  </p>
                </div>

                {/* 2-Column Priorities */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* High Priority Findings */}
                  <div className="p-4 rounded-lg bg-neutral-900/40 border border-neutral-800 space-y-2">
                    <h4 className="text-xs font-mono uppercase text-crimson-light flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5" /> Highest Priority Findings
                    </h4>
                    <ul className="space-y-1.5 text-xs text-neutral-300">
                      {(assessment.highest_priority_findings || []).map((item, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-crimson font-mono">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* High Priority Attack Paths */}
                  <div className="p-4 rounded-lg bg-neutral-900/40 border border-neutral-800 space-y-2">
                    <h4 className="text-xs font-mono uppercase text-amber-400 flex items-center gap-1.5">
                      <Sliders className="h-3.5 w-3.5" /> High Priority Attack Paths
                    </h4>
                    <ul className="space-y-1.5 text-xs text-neutral-300">
                      {(assessment.highest_priority_attack_paths || []).map((item, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-amber-400 font-mono">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Deterministic Risk Interpretation */}
                <div className="space-y-1.5">
                  <h3 className="text-xs font-mono uppercase text-neutral-400">Deterministic Risk Model Reference</h3>
                  <div className="p-3.5 rounded-lg bg-neutral-900/60 border border-neutral-800 text-xs text-neutral-300 leading-relaxed font-mono">
                    {assessment.risk_interpretation}
                  </div>
                </div>

                {/* Recommended Human Actions */}
                <div className="space-y-2">
                  <h3 className="text-xs font-mono uppercase text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Recommended Human Investigative Actions
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {(assessment.recommended_human_actions || []).map((act, idx) => (
                      <div key={idx} className="p-3 rounded bg-emerald-950/20 border border-emerald-900/40 text-xs text-emerald-200 flex items-start gap-2">
                        <span className="font-mono text-emerald-400 font-bold">{idx + 1}.</span>
                        <span>{act}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Specialized Agent Execution Breakdown */}
            <div className="space-y-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Bot className="h-4 w-4 text-crimson" />
                Specialized Agent Execution Breakdown ({detail.agent_runs.length})
              </h2>

              <div className="space-y-2">
                {detail.agent_runs.map((agent: TeamAgentRun) => {
                  const isExpanded = expandedAgent === agent.agent_name;
                  return (
                    <div
                      key={agent.id}
                      className="rounded-lg bg-background-secondary border border-border-subtle overflow-hidden"
                    >
                      <button
                        onClick={() => setExpandedAgent(isExpanded ? null : agent.agent_name)}
                        className="w-full p-4 flex items-center justify-between text-left hover:bg-neutral-800/40 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded bg-neutral-900 border border-neutral-700 flex items-center justify-center">
                            {getAgentIcon(agent.agent_name)}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm font-semibold text-white uppercase">
                                {agent.agent_name}
                              </span>
                              {getStatusBadge(agent.status)}
                            </div>
                            <p className="text-xs text-neutral-400 font-mono mt-0.5">
                              Model: {agent.model_used || "deterministic-model"} • Version: {agent.prompt_version || "v1"}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4 text-xs font-mono text-neutral-400">
                          <span>Confidence: <strong className="text-neutral-200">{(agent.confidence * 100).toFixed(0)}%</strong></span>
                          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-4 border-t border-border-subtle bg-neutral-950/40 space-y-3">
                          <div className="text-xs text-neutral-300">
                            <span className="font-mono text-neutral-500 uppercase text-[10px] block mb-1">
                              Structured Output
                            </span>
                            <pre className="p-3 rounded bg-neutral-900 border border-neutral-800 text-[11px] font-mono text-neutral-200 overflow-x-auto max-h-72">
                              {JSON.stringify(agent.output, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Human Sign-Off Modal */}
            {showReviewModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
                <div className="w-full max-w-lg rounded-xl bg-background-secondary border border-border-subtle p-6 space-y-4 shadow-2xl">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-crimson" />
                      Sign Off / Human Review
                    </h3>
                    <p className="text-xs text-neutral-400 mt-1">
                      Record human verification notes and close the review boundary for this assessment.
                    </p>
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                      Review & Triage Notes
                    </label>
                    <textarea
                      rows={4}
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      placeholder="e.g., Reviewed findings with backend lead. SQL injection confirmed and patch PR scheduled for sprint 42."
                      className="w-full px-3 py-2 rounded bg-neutral-900 border border-neutral-700 text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                    />
                  </div>

                  <div className="flex justify-end gap-3 pt-2 border-t border-border-subtle">
                    <button
                      type="button"
                      onClick={() => setShowReviewModal(false)}
                      disabled={submittingReview}
                      className="px-4 py-2 rounded border border-neutral-700 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-xs font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleReviewSubmit}
                      disabled={submittingReview}
                      className="px-4 py-2 rounded bg-crimson hover:bg-crimson/90 text-white text-xs font-medium flex items-center gap-2 disabled:opacity-50"
                    >
                      {submittingReview ? <RotateCw className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                      {submittingReview ? "Submitting..." : "Confirm Sign-Off"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </CommandCenterShell>
  );
}
