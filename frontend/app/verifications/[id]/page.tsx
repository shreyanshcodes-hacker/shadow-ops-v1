"use client";

import React, { useState, useEffect, useCallback, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowLeft,
  RefreshCw,
  FileCode,
  GitCommit,
  Check,
  Clock,
  Layers,
  Terminal,
} from "lucide-react";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import {
  VerificationJob,
  VerificationComparison,
  VerificationRegressionCheck,
  VerificationReview,
} from "@/types";

export default function VerificationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const jobId = resolvedParams.id;
  const router = useRouter();
  const { activeWorkspace } = useWorkspace();

  const [job, setJob] = useState<VerificationJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Review modal state
  const [reviewDecision, setReviewDecision] = useState<"accepted" | "rejected" | null>(null);
  const [rationale, setRationale] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const fetchJobDetails = useCallback(async () => {
    if (!activeWorkspace) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<VerificationJob>(
        `/verifications/${jobId}?workspace_id=${activeWorkspace.id}`
      );
      setJob(res);
    } catch (err: unknown) {
      console.error("Failed to fetch verification details:", err);
      setError("Unable to load verification details. Please verify workspace privileges.");
    } finally {
      setIsLoading(false);
    }
  }, [jobId, activeWorkspace]);

  useEffect(() => {
    fetchJobDetails();
  }, [fetchJobDetails]);

  const handleRerun = async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    try {
      const res = await apiClient.post<VerificationJob>(
        `/verifications/${jobId}/rerun?workspace_id=${activeWorkspace.id}`
      );
      router.push(`/verifications/${res.id}`);
    } catch (err: unknown) {
      console.error("Rerun failed:", err);
      setError("Failed to rerun verification.");
      setIsLoading(false);
    }
  };

  const submitReview = async () => {
    if (!reviewDecision || !activeWorkspace) return;
    if (rationale.trim().length < 5) {
      setReviewError("Rationale must be at least 5 characters.");
      return;
    }

    setIsSubmittingReview(true);
    setReviewError(null);
    try {
      await apiClient.post<VerificationReview>(
        `/verifications/${jobId}/review?workspace_id=${activeWorkspace.id}`,
        {
          decision: reviewDecision,
          rationale: rationale.trim(),
        }
      );
      setReviewDecision(null);
      setRationale("");
      await fetchJobDetails();
    } catch (err: unknown) {
      console.error("Review failed:", err);
      setReviewError("Failed to submit review. Only Admins and Security Engineers can sign off.");
    } finally {
      setIsSubmittingReview(false);
    }
  };

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

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case "NO_LONGER_DETECTED":
        return <Badge variant="success">NO LONGER DETECTED</Badge>;
      case "STILL_PRESENT":
        return <Badge variant="critical">STILL PRESENT</Badge>;
      case "MODIFIED_OR_MOVED":
        return <Badge variant="critical">MODIFIED / MOVED</Badge>;
      case "POSSIBLE_REGRESSION":
        return <Badge variant="critical">REGRESSION DETECTED</Badge>;
      default:
        return <Badge variant="default">{cat}</Badge>;
    }
  };

  if (isLoading && !job) {
    return (
      <CommandCenterShell>
        <div className="py-24 text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto text-neutral-500 mb-3" />
          <p className="text-sm text-neutral-400">Loading independent verification analysis...</p>
        </div>
      </CommandCenterShell>
    );
  }

  if (error || !job) {
    return (
      <CommandCenterShell>
        <div className="p-8 max-w-4xl mx-auto space-y-4">
          <Link href="/verifications">
            <Button variant="outline" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" /> Back to Verifications
            </Button>
          </Link>
          <div className="p-4 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300">
            {error || "Verification job not found."}
          </div>
        </div>
      </CommandCenterShell>
    );
  }

  const latestReview = job.reviews && job.reviews.length > 0 ? job.reviews[0] : null;

  return (
    <CommandCenterShell>
      <div className="p-8 max-w-6xl mx-auto space-y-6">
        {/* Navigation & Header */}
        <div className="flex items-center justify-between border-b border-border-subtle pb-4">
          <div className="flex items-center gap-3">
            <Link href="/verifications">
              <Button variant="outline" size="sm" className="gap-2 border-border-subtle hover:bg-neutral-800">
                <ArrowLeft className="h-4 w-4" /> Back
              </Button>
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white font-mono">
                  VERIFICATION JOB: {job.id.slice(0, 13)}
                </h1>
                {getVerdictBadge(job.policy_verdict)}
              </div>
              <p className="text-xs text-neutral-400 mt-0.5">
                Evaluated under policy <code className="text-neutral-300">{job.policy_version}</code>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRerun}
              disabled={isLoading}
              className="gap-2 border-border-subtle hover:bg-neutral-800"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Rerun Verification
            </Button>
          </div>
        </div>

        {/* Core Invariant Alert */}
        <div className="bg-neutral-900/60 border border-emerald-500/30 rounded-xl p-4 flex items-start gap-3">
          <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-semibold text-emerald-200">
              Deterministic Fix Verification Invariant Enforced
            </p>
            <p className="text-neutral-400">
              Software and scans can only nominate a <strong>VERIFIED CANDIDATE</strong>.
              Finding state is not automatically altered. A human security engineer or workspace admin must review the evidence below and sign off.
            </p>
          </div>
        </div>

        {/* Sub-outcomes Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-neutral-900/40 border-border-subtle">
            <CardContent className="p-4">
              <span className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold">
                Vulnerability Status
              </span>
              <div className="mt-2 flex items-center gap-2">
                {getCategoryBadge(job.vulnerability_status)}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900/40 border-border-subtle">
            <CardContent className="p-4">
              <span className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold">
                Regression Status
              </span>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant={job.regression_status === "PASS" ? "success" : "critical"}>
                  {job.regression_status}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900/40 border-border-subtle">
            <CardContent className="p-4">
              <span className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold">
                Scanner Completion
              </span>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant={job.scanner_status === "COMPLETED" ? "success" : "critical"}>
                  {job.scanner_status}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900/40 border-border-subtle">
            <CardContent className="p-4">
              <span className="text-[11px] text-neutral-400 uppercase tracking-wider font-semibold">
                Unit Test Status
              </span>
              <div className="mt-2 flex items-center gap-2">
                <Badge variant={job.test_status === "PASS" ? "success" : "default"}>
                  {job.test_status}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Policy Reasons */}
        {job.policy_reasons && job.policy_reasons.length > 0 && (
          <Card className="bg-neutral-900/40 border-border-subtle">
            <CardHeader className="py-3 px-4 border-b border-border-subtle">
              <CardTitle className="text-xs uppercase tracking-wider text-neutral-400 font-semibold">
                Policy Verdict Reasons ({job.policy_version})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-2">
              {job.policy_reasons.map((reason, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-neutral-300">
                  <span className="text-emerald-400 font-mono">•</span>
                  <span>{reason}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Evidence Comparisons */}
        <Card className="bg-neutral-900/40 border-border-subtle">
          <CardHeader className="py-3 px-4 border-b border-border-subtle flex flex-row items-center justify-between">
            <CardTitle className="text-xs uppercase tracking-wider text-neutral-400 font-semibold flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-400" />
              Baseline vs Rescan Evidence Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            {job.comparisons && job.comparisons.length > 0 ? (
              job.comparisons.map((comp) => (
                <div
                  key={comp.id}
                  className="p-4 rounded-lg bg-neutral-950/60 border border-neutral-800 space-y-3"
                >
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-white">
                        {comp.rule_id}
                      </span>
                      <code className="text-xs text-neutral-400">{comp.file_path}</code>
                    </div>
                    {getCategoryBadge(comp.comparison_category)}
                  </div>

                  <p className="text-xs text-neutral-300 bg-neutral-900/80 p-2.5 rounded border border-neutral-800">
                    {comp.explanation}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded bg-neutral-900/50 border border-neutral-800">
                      <span className="text-[10px] uppercase font-bold text-neutral-400 block mb-1">
                        Pre-Patch Baseline Evidence
                      </span>
                      <pre className="text-[11px] font-mono text-red-300 whitespace-pre-wrap bg-neutral-950 p-2 rounded overflow-x-auto">
                        {comp.baseline_evidence?.code_snippet as string || "No code snippet recorded"}
                      </pre>
                    </div>

                    <div className="p-3 rounded bg-neutral-900/50 border border-neutral-800">
                      <span className="text-[10px] uppercase font-bold text-neutral-400 block mb-1">
                        Post-Patch Independent Rescan
                      </span>
                      {comp.rescan_evidence && Object.keys(comp.rescan_evidence).length > 0 ? (
                        <pre className="text-[11px] font-mono text-neutral-300 whitespace-pre-wrap bg-neutral-950 p-2 rounded overflow-x-auto">
                          {JSON.stringify(comp.rescan_evidence, null, 2)}
                        </pre>
                      ) : (
                        <div className="text-xs text-emerald-400 p-3 bg-neutral-950 rounded flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4" />
                          No finding detected in rescan matching target flaw.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-neutral-500 py-4 text-center">
                No comparison records available for this run.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Regression Checks Table */}
        <Card className="bg-neutral-900/40 border-border-subtle">
          <CardHeader className="py-3 px-4 border-b border-border-subtle">
            <CardTitle className="text-xs uppercase tracking-wider text-neutral-400 font-semibold flex items-center gap-2">
              <Terminal className="h-4 w-4 text-emerald-400" />
              Automated Regression Checks
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-neutral-950/60 text-neutral-400 border-b border-border-subtle">
                  <tr>
                    <th className="py-2.5 px-4 font-semibold">Check Name</th>
                    <th className="py-2.5 px-4 font-semibold">Status</th>
                    <th className="py-2.5 px-4 font-semibold">Duration</th>
                    <th className="py-2.5 px-4 font-semibold">Output Summary</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {job.regression_checks && job.regression_checks.length > 0 ? (
                    job.regression_checks.map((chk) => (
                      <tr key={chk.id} className="hover:bg-neutral-800/30">
                        <td className="py-2.5 px-4 font-mono font-medium text-white">
                          {chk.check_name}
                        </td>
                        <td className="py-2.5 px-4">
                          <Badge variant={chk.status === "PASS" ? "success" : "critical"}>
                            {chk.status}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-4 text-neutral-400 font-mono">
                          {chk.duration_ms} ms
                        </td>
                        <td className="py-2.5 px-4 text-neutral-300">
                          {chk.output_summary}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="py-4 text-center text-neutral-500">
                        No regression checks recorded.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Human Sign-Off Gate Card */}
        <Card className="bg-neutral-900/60 border-border-subtle">
          <CardHeader className="py-3 px-4 border-b border-border-subtle">
            <CardTitle className="text-xs uppercase tracking-wider text-neutral-400 font-semibold flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              Human Review & Finding Closure Gate
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {latestReview ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-neutral-400">Review Decision:</span>
                  <Badge variant={latestReview.decision === "accepted" ? "success" : "critical"}>
                    {latestReview.decision.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-neutral-500 font-mono">
                    at {new Date(latestReview.reviewed_at).toLocaleString()}
                  </span>
                </div>

                <div className="p-4 rounded bg-neutral-950 border border-neutral-800 text-xs text-neutral-300 space-y-1">
                  <span className="font-semibold text-white block">Reviewer Rationale:</span>
                  <p>{latestReview.rationale}</p>
                </div>

                <div className="text-xs text-neutral-400 flex items-center gap-2">
                  <span>Finding Status After Review:</span>
                  <Badge variant={latestReview.finding_status_after === "fixed" ? "success" : "default"}>
                    {latestReview.finding_status_after.toUpperCase()}
                  </Badge>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-xs text-neutral-300">
                  Review the independent rescan and regression checks above. As a workspace Admin or Security Engineer, you can either accept the fix (which closes the finding as resolved) or reject the fix (which keeps the finding open).
                </p>

                {reviewError && (
                  <div className="p-3 rounded bg-red-950/40 border border-red-500/30 text-red-300 text-xs">
                    {reviewError}
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-xs font-semibold text-neutral-300">
                    Review Rationale & Justification (Required)
                  </label>
                  <textarea
                    rows={3}
                    value={rationale}
                    onChange={(e) => setRationale(e.target.value)}
                    placeholder="Provide justification for accepting or rejecting this fix..."
                    className="w-full rounded bg-neutral-950 border border-neutral-700 p-2.5 text-xs text-white focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={isSubmittingReview || !rationale.trim()}
                    onClick={() => {
                      setReviewDecision("accepted");
                      submitReview();
                    }}
                    className="gap-2 bg-emerald-600 hover:bg-emerald-500 text-white"
                  >
                    <Check className="h-4 w-4" />
                    Accept Fix & Close Finding
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isSubmittingReview || !rationale.trim()}
                    onClick={() => {
                      setReviewDecision("rejected");
                      submitReview();
                    }}
                    className="gap-2 border-red-500/40 text-red-400 hover:bg-red-950/50"
                  >
                    <XCircle className="h-4 w-4" />
                    Reject Fix (Keep Finding Open)
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </CommandCenterShell>
  );
}
