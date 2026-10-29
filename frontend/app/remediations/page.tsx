"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Wrench,
  ShieldCheck,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  FileCode,
  ArrowRight,
  Filter,
  RefreshCw,
  GitCommit,
  Check,
} from "lucide-react";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { apiClient } from "@/lib/api-client";
import { RemediationProposal, RemediationListResponse } from "@/types";

export default function RemediationsPage() {
  const [proposals, setProposals] = useState<RemediationProposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [error, setError] = useState<string | null>(null);

  const fetchProposals = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const activeWs = typeof window !== "undefined"
        ? localStorage.getItem("shadowops_active_workspace") || "default"
        : "default";

      const url = statusFilter === "ALL"
        ? `/remediations?workspace_id=${activeWs}`
        : `/remediations?workspace_id=${activeWs}&status=${statusFilter}`;

      const res = await apiClient.get<RemediationListResponse>(url);
      setProposals(res.items || []);
    } catch (err: unknown) {
      console.error("Failed to fetch remediation proposals:", err);
      setError("Unable to load remediation proposals. Please check workspace connection.");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchProposals();
  }, [fetchProposals]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "AWAITING_APPROVAL":
        return <Badge variant="medium">AWAITING APPROVAL</Badge>;
      case "APPROVED":
        return <Badge variant="info">APPROVED (READY TO APPLY)</Badge>;
      case "APPLIED":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-600/50">
            <CheckCircle className="h-3 w-3" />
            APPLIED — VERIFICATION PENDING
          </span>
        );
      case "VALIDATING":
        return <Badge variant="default">VALIDATING...</Badge>;
      case "VALIDATION_FAILED":
        return <Badge variant="critical">VALIDATION FAILED</Badge>;
      case "REJECTED":
        return <Badge variant="critical">REJECTED</Badge>;
      case "ROLLED_BACK":
        return <Badge variant="default">ROLLED BACK</Badge>;
      case "FAILED":
        return <Badge variant="critical">FAILED</Badge>;
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <CommandCenterShell>
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border-subtle">
          <div>
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Wrench className="h-4 w-4" />
              </div>
              <h1 className="text-xl font-bold text-white tracking-wide">
                Remediation & Patch Management
              </h1>
            </div>
            <p className="text-xs text-neutral-400 mt-1">
              AI-generated code patches with strict sandbox verification, human approval sign-offs, and atomic rollback.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchProposals()}
              disabled={isLoading}
              className="gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-2 bg-neutral-900/50 p-2 rounded-lg border border-border-subtle">
          <Filter className="h-3.5 w-3.5 text-neutral-400 ml-2 mr-1" />
          <span className="text-xs text-neutral-400 font-mono">STATUS:</span>
          {["ALL", "AWAITING_APPROVAL", "APPROVED", "APPLIED", "VALIDATION_FAILED", "REJECTED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 text-xs rounded transition-all font-mono ${
                statusFilter === st
                  ? "bg-crimson text-white font-semibold"
                  : "text-neutral-400 hover:text-white hover:bg-neutral-800"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Proposals List */}
        {isLoading ? (
          <div className="grid grid-cols-1 gap-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="animate-pulse h-32 bg-neutral-900/30" />
            ))}
          </div>
        ) : proposals.length === 0 ? (
          <Card variant="bordered" className="p-12 text-center">
            <div className="max-w-md mx-auto space-y-3">
              <div className="h-12 w-12 rounded-full bg-neutral-800/80 mx-auto flex items-center justify-center text-neutral-400">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h3 className="text-base font-semibold text-white">No Remediation Proposals Found</h3>
              <p className="text-xs text-neutral-400">
                When security findings are analyzed, you can generate verified code patches directly from the Findings details page.
              </p>
              <div className="pt-2">
                <Link href="/scans">
                  <Button variant="outline" size="sm">
                    View Scans & Findings
                  </Button>
                </Link>
              </div>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {proposals.map((proposal) => (
              <Card
                key={proposal.id}
                variant="bordered"
                className="hover:border-neutral-700 transition-colors"
              >
                <CardContent className="p-5">
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {getStatusBadge(proposal.status)}
                        <span className="text-[10px] text-neutral-500 font-mono">
                          v{proposal.version}
                        </span>
                        <span className="text-[10px] text-neutral-500 font-mono">
                          SHA: {proposal.patch_hash.slice(0, 10)}...
                        </span>
                      </div>

                      <h3 className="text-base font-semibold text-white hover:text-crimson-light transition-colors">
                        <Link href={`/remediations/${proposal.id}`}>
                          {proposal.proposal_title}
                        </Link>
                      </h3>

                      <p className="text-xs text-neutral-400 line-clamp-2">
                        {proposal.problem_summary || proposal.proposed_solution}
                      </p>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-neutral-400 pt-1">
                        <div className="flex items-center gap-1 font-mono">
                          <FileCode className="h-3.5 w-3.5 text-neutral-500" />
                          <span>{proposal.affected_files?.join(", ") || "None"}</span>
                        </div>
                        <div className="flex items-center gap-1 font-mono">
                          <Clock className="h-3.5 w-3.5 text-neutral-500" />
                          <span>{new Date(proposal.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex md:flex-col items-center md:items-end justify-between gap-2 shrink-0">
                      <Link href={`/remediations/${proposal.id}`}>
                        <Button variant="primary" size="sm" className="gap-1.5">
                          Review Patch
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </CommandCenterShell>
  );
}
