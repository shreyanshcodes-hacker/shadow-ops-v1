"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ArrowRight,
  RefreshCw,
  ShieldCheck,
  FileCheck,
  Search,
} from "lucide-react";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { VerificationJob, VerificationListResponse, Finding } from "@/types";

export default function VerificationsPage() {
  const { activeWorkspace } = useWorkspace();
  const [jobs, setJobs] = useState<VerificationJob[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<string>("ALL");
  const [error, setError] = useState<string | null>(null);

  // Trigger modal state
  const [showTriggerModal, setShowTriggerModal] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState("");
  const [triggering, setTriggering] = useState(false);

  const fetchJobs = useCallback(async () => {
    if (!activeWorkspace) {
      setJobs([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<VerificationListResponse>(
        `/verifications?workspace_id=${activeWorkspace.id}`
      );
      setJobs(res.items || []);
    } catch (err: unknown) {
      console.error("Failed to fetch verification runs:", err);
      setError("Unable to load verification runs. Please check workspace connection.");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleOpenTriggerModal = async () => {
    if (!activeWorkspace) return;
    setShowTriggerModal(true);
    try {
      const list = await apiClient.get<Finding[]>(`/findings?workspace_id=${activeWorkspace.id}`);
      setFindings(list);
      if (list.length > 0 && !selectedFindingId) {
        setSelectedFindingId(list[0].id);
      }
    } catch (err) {
      console.error("Failed to load findings for verification:", err);
    }
  };

  const handleTriggerVerification = async () => {
    if (!activeWorkspace || !selectedFindingId) return;
    setTriggering(true);
    try {
      const res = await apiClient.post<VerificationJob>(
        `/findings/${selectedFindingId}/verify?workspace_id=${activeWorkspace.id}`
      );
      setJobs((prev) => [res, ...prev]);
      setShowTriggerModal(false);
    } catch (err: any) {
      console.error("Failed to trigger verification:", err);
      alert(err?.message || "Failed to trigger fix verification.");
    } finally {
      setTriggering(false);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    if (filter === "ALL") return true;
    if (filter === "PENDING_REVIEW") return job.status === "PASSED_PENDING_REVIEW";
    if (filter === "VERIFIED_CANDIDATE") return job.policy_verdict === "VERIFIED_CANDIDATE";
    if (filter === "FAILED") return job.policy_verdict === "FAILED" || job.status === "FAILED";
    return true;
  });

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case "VERIFIED_CANDIDATE":
        return <Badge variant="success">VERIFIED CANDIDATE</Badge>;
      case "FAILED":
        return <Badge variant="critical">FAILED VERIFICATION</Badge>;
      case "BLOCKED":
        return <Badge variant="critical">BLOCKED</Badge>;
      case "INCONCLUSIVE":
        return <Badge variant="medium">INCONCLUSIVE</Badge>;
      default:
        return <Badge variant="default">{verdict}</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PASSED_PENDING_REVIEW":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-600/50">
            <CheckCircle2 className="h-3 w-3" />
            PASSED — PENDING HUMAN REVIEW
          </span>
        );
      case "RUNNING":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-blue-950/60 text-blue-300 border border-blue-600/50">
            <RefreshCw className="h-3 w-3 animate-spin" />
            RUNNING VERIFICATION...
          </span>
        );
      case "FAILED":
        return <Badge variant="critical">FAILED</Badge>;
      case "BLOCKED":
        return <Badge variant="critical">BLOCKED</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <CommandCenterShell>
      <div className="p-8 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-subtle pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                  Independent Fix Verification
                  <span className="text-xs px-2 py-0.5 rounded border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 font-mono">
                    STAGE 9
                  </span>
                </h1>
                <p className="text-sm text-neutral-400 mt-1">
                  Automated baseline comparison, independent rescan, and regression checks with mandatory human sign-off.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchJobs}
              disabled={isLoading}
              className="gap-2 border-border-subtle hover:bg-neutral-800"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleOpenTriggerModal}
              disabled={!activeWorkspace}
              className="gap-2 bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              <ShieldCheck className="h-4 w-4" />
              Trigger Fix Verification
            </Button>
          </div>
        </div>

        {/* Verification Policy Banner */}
        <div className="bg-neutral-900/60 border border-border-subtle rounded-xl p-4 flex items-center justify-between text-xs text-neutral-300">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-white">Verification Engine:</span>
            <code className="px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-300 font-mono text-[11px]">
              verification-policy-v1
            </code>
            <span className="text-neutral-500">•</span>
            <span className="text-neutral-400">
              No sufficient evidence means no verified fix. Only authorized human review closes findings.
            </span>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 border-b border-border-subtle pb-3">
          {["ALL", "PENDING_REVIEW", "VERIFIED_CANDIDATE", "FAILED"].map((tab) => (
            <button
              key={tab}
              onClick={() => setFilter(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === tab
                  ? "bg-neutral-800 text-white border border-neutral-700"
                  : "text-neutral-400 hover:text-white hover:bg-neutral-800/50"
              }`}
            >
              {tab.replace("_", " ")}
            </button>
          ))}
        </div>

        {/* Error message */}
        {error && (
          <div className="p-4 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-sm flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Jobs List */}
        {isLoading ? (
          <div className="py-20 text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-neutral-500 mb-3" />
            <p className="text-sm text-neutral-400">Loading independent verification runs...</p>
          </div>
        ) : filteredJobs.length === 0 ? (
          <Card className="bg-neutral-900/40 border-border-subtle">
            <CardContent className="py-16 text-center">
              <FileCheck className="h-10 w-10 text-neutral-600 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-white">No Verification Runs Found</h3>
              <p className="text-sm text-neutral-400 mt-1 max-w-md mx-auto">
                Trigger fix verification from an applied remediation proposal or directly on a finding.
              </p>
              <div className="mt-6 flex justify-center gap-3">
                <Link href="/remediations">
                  <Button variant="outline" size="sm" className="gap-2">
                    View Applied Remediations
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {filteredJobs.map((job) => (
              <Card
                key={job.id}
                className="bg-neutral-900/40 border-border-subtle hover:border-neutral-700 transition-all"
              >
                <CardContent className="p-5">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        {getVerdictBadge(job.policy_verdict)}
                        {getStatusBadge(job.status)}
                        <span className="text-xs text-neutral-500 font-mono">
                          ID: {job.id.slice(0, 8)}
                        </span>
                      </div>

                      <div className="text-sm font-semibold text-white">
                        Vulnerability: {job.baseline_snapshot?.rule_id as string || "Security Finding"}
                      </div>

                      <div className="flex items-center gap-4 text-xs text-neutral-400 flex-wrap">
                        <span className="flex items-center gap-1">
                          File: <code className="text-neutral-300 font-mono">{job.baseline_snapshot?.file_path as string || "code"}</code>
                        </span>
                        <span>•</span>
                        <span>Vulnerability: <strong className="text-neutral-300 font-mono">{job.vulnerability_status}</strong></span>
                        <span>•</span>
                        <span>Regression Checks: <strong className="text-neutral-300 font-mono">{job.regression_status}</strong></span>
                        <span>•</span>
                        <span>Scanner: <strong className="text-neutral-300 font-mono">{job.scanner_status}</strong></span>
                      </div>

                      {job.policy_reasons && job.policy_reasons.length > 0 && (
                        <p className="text-xs text-neutral-400 line-clamp-1 italic">
                          &ldquo;{job.policy_reasons[0]}&rdquo;
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <Link href={`/verifications/${job.id}`}>
                        <Button variant="outline" size="sm" className="gap-2 border-border-subtle hover:bg-neutral-800">
                          Inspect Evidence
                          <ArrowRight className="h-4 w-4" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Trigger Fix Verification Modal */}
        {showTriggerModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="w-full max-w-lg rounded-xl bg-background-secondary border border-border-subtle p-6 space-y-5 shadow-2xl">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-emerald-400" />
                  Trigger Independent Fix Verification
                </h3>
                <p className="text-xs text-neutral-400 mt-1">
                  Runs baseline comparison, regression suite, and independent rescan for a target finding in {activeWorkspace?.name}.
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                    Target Security Finding to Verify
                  </label>
                  {findings.length === 0 ? (
                    <div className="p-4 rounded bg-neutral-900 border border-neutral-700 text-xs text-neutral-400 text-center">
                      No findings available in this workspace. Run a code scan first.
                    </div>
                  ) : (
                    <select
                      value={selectedFindingId}
                      onChange={(e) => setSelectedFindingId(e.target.value)}
                      className="w-full px-3 py-2 rounded bg-neutral-900 border border-neutral-700 text-neutral-200 text-sm focus:outline-none focus:border-emerald-500"
                    >
                      {findings.map((f) => (
                        <option key={f.id} value={f.id}>
                          [{f.severity.toUpperCase()}] {f.title} ({f.status})
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-900/30 text-xs text-emerald-300">
                  <p className="font-semibold mb-0.5">Automated Policy Enforcement:</p>
                  <p className="text-neutral-400">
                    The verification engine checks for syntax errors, boundary violations, and scanner elimination. A human security engineer or admin review is still required to permanently close the finding.
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-border-subtle">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowTriggerModal(false)}
                  disabled={triggering}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  size="sm"
                  onClick={handleTriggerVerification}
                  disabled={triggering || !selectedFindingId}
                  className="gap-2 bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                  {triggering ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                  {triggering ? "Running Rescan..." : "Start Verification"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </CommandCenterShell>
  );
}
