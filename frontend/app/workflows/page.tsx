"use client";

import React, { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { WorkflowRunItem, WorkflowRunListResponse } from "@/types";
import {
  Sliders,
  Play,
  RotateCw,
  CheckCircle2,
  XCircle,
  Clock,
  Shield,
  Lock,
  Code,
  Info,
} from "lucide-react";

export default function WorkflowsPage() {
  const { activeWorkspace } = useWorkspace();
  const [runs, setRuns] = useState<WorkflowRunItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<WorkflowRunItem | null>(null);

  const fetchWorkflowRuns = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    try {
      const res = await apiClient.get<WorkflowRunListResponse>(
        `/workflows/runs?workspace_id=${activeWorkspace.id}`
      );
      setRuns(res.items || []);
    } catch (err) {
      console.error("Failed to load workflow runs:", err);
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflowRuns();
  }, [activeWorkspace]);

  const handleRetry = async (runId: string) => {
    if (!activeWorkspace) return;
    setRetryingId(runId);
    try {
      const updated = await apiClient.post<WorkflowRunItem>(
        `/workflows/runs/${runId}/retry?workspace_id=${activeWorkspace.id}`,
        {}
      );
      setRuns((prev) => prev.map((r) => (r.id === runId ? updated : r)));
    } catch (err) {
      console.error("Retry failed:", err);
      alert(`Retry failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setRetryingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="success">Completed</Badge>;
      case "failed":
        return <Badge variant="critical">Failed</Badge>;
      case "running":
        return <Badge variant="info">Running</Badge>;
      case "queued":
        return <Badge variant="outline">Queued</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-subtle pb-5">
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                <Sliders className="h-5 w-5 text-crimson" />
                Controlled Workflow Automation
              </h1>
              <p className="text-xs text-neutral-400 mt-1">
                Audited execution history for policy-governed automation tasks, webhook dispatches, and compliance snapshots.
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={fetchWorkflowRuns}
              disabled={loading}
              className="text-xs flex items-center gap-1.5"
            >
              <RotateCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>

          {/* Security Boundary Notice */}
          <div className="p-4 rounded-lg bg-background-secondary/80 border border-crimson/30 flex items-start gap-3">
            <Shield className="h-5 w-5 text-crimson shrink-0 mt-0.5" />
            <div className="space-y-1 text-xs">
              <span className="font-semibold text-white">Strict Security Boundary Invariant</span>
              <p className="text-neutral-400 leading-relaxed">
                Workflows operate strictly via pre-approved allowlists. Arbitrary user-authored scripts, shell commands, and untrusted network endpoints are strictly forbidden. Automation can never bypass human remediation approval or alter verified finding states.
              </p>
            </div>
          </div>

          {/* Runs List & Details */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-3">
              <div className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center justify-between">
                <span>Execution History</span>
                <span className="font-mono text-neutral-500">{runs.length} Runs</span>
              </div>

              {loading ? (
                <div className="text-center py-16 text-neutral-500 font-mono text-xs">
                  Loading workflow runs...
                </div>
              ) : runs.length === 0 ? (
                <EmptyState
                  title="No Workflow Runs"
                  description="No automated workflows have executed yet in this workspace."
                />
              ) : (
                runs.map((run) => {
                  const isSelected = selectedRun?.id === run.id;
                  return (
                    <div
                      key={run.id}
                      onClick={() => setSelectedRun(run)}
                      className={`p-4 rounded-lg border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-background-secondary border-crimson/60 shadow-sm"
                          : "bg-background-secondary/50 border-border-subtle hover:bg-background-tertiary/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-white">
                              {run.workflow_name}
                            </span>
                            {getStatusBadge(run.status)}
                          </div>
                          <div className="text-xs font-mono text-neutral-400">
                            Action: <span className="text-cyan-400">{run.action_name}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {run.status === "failed" && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRetry(run.id);
                              }}
                              disabled={retryingId === run.id}
                              className="text-xs h-7 px-2 border-red-800 text-red-300 hover:bg-red-950/40"
                            >
                              <RotateCw className={`h-3 w-3 mr-1 ${retryingId === run.id ? "animate-spin" : ""}`} />
                              Retry
                            </Button>
                          )}
                        </div>
                      </div>

                      <div className="mt-3 flex items-center gap-4 text-[11px] font-mono text-neutral-500">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(run.created_at).toLocaleString()}
                        </span>
                        {run.idempotency_key && (
                          <span className="truncate max-w-[200px]" title={run.idempotency_key}>
                            Key: {run.idempotency_key}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Selected Run Payload Inspector */}
            <div className="space-y-3">
              <div className="text-xs font-semibold text-neutral-300 uppercase tracking-wider">
                Payload Inspector
              </div>

              {selectedRun ? (
                <Card className="border-border-subtle bg-background-secondary/60">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-xs font-semibold text-white flex items-center justify-between">
                      <span>{selectedRun.workflow_name}</span>
                      {getStatusBadge(selectedRun.status)}
                    </CardTitle>
                    <CardDescription className="text-[11px] font-mono text-neutral-400">
                      ID: {selectedRun.id}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4 text-xs font-mono">
                    <div>
                      <div className="text-[11px] text-neutral-400 font-semibold mb-1 flex items-center gap-1">
                        <Code className="h-3 w-3" />
                        Input Data:
                      </div>
                      <pre className="p-2.5 rounded bg-background border border-border-subtle text-[11px] overflow-x-auto text-neutral-300">
                        {JSON.stringify(selectedRun.input_data, null, 2)}
                      </pre>
                    </div>

                    <div>
                      <div className="text-[11px] text-neutral-400 font-semibold mb-1 flex items-center gap-1">
                        <Code className="h-3 w-3" />
                        Output Data:
                      </div>
                      <pre className="p-2.5 rounded bg-background border border-border-subtle text-[11px] overflow-x-auto text-neutral-300">
                        {JSON.stringify(selectedRun.output_data, null, 2)}
                      </pre>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card className="border-border-subtle bg-background-secondary/30 p-8 text-center text-xs text-neutral-500 font-mono">
                  Select a workflow run from the left to inspect input parameters and execution outputs.
                </Card>
              )}
            </div>
          </div>
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
