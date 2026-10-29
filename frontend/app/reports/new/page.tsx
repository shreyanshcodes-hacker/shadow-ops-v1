"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { Asset, ReportType, ReportFormat, SecurityReport } from "@/types";
import {
  FileText,
  ArrowLeft,
  ShieldAlert,
  Sparkles,
  CheckCircle2,
  Lock,
  Layers,
  FileCheck,
} from "lucide-react";

export default function NewReportPage() {
  const router = useRouter();
  const { activeWorkspace } = useWorkspace();

  const [reportType, setReportType] = useState<ReportType>("executive_summary");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [format, setFormat] = useState<ReportFormat>("pdf");
  const [includeAiSummary, setIncludeAiSummary] = useState(true);
  const [selectedSeverities, setSelectedSeverities] = useState<string[]>(["critical", "high", "medium", "low"]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspace) return;
    apiClient
      .get<Asset[]>(`/workspaces/${activeWorkspace.id}/assets`)
      .then((data) => setAssets(data || []))
      .catch((err) => console.error("Failed to fetch assets for filter:", err));
  }, [activeWorkspace]);

  const reportTypeDescriptions: Record<ReportType, { title: string; desc: string }> = {
    executive_summary: {
      title: "Executive Posture Summary",
      desc: "High-level overview designed for startup founders, board members, and engineering leads. Includes deterministic risk scores, critical attack paths, and advisory AI analysis.",
    },
    technical_vulnerability: {
      title: "Technical Vulnerability Ledger",
      desc: "Granular breakdown of verified scanner findings with code locations, CWE/OWASP categorizations, redacted code snippets, and remediation associations.",
    },
    remediation_progress: {
      title: "Remediation & Patch Progress",
      desc: "Lifecycle tracking of remediation proposals, human approvals, applied git revisions, and rollback checkpoint statuses.",
    },
    verification_regression: {
      title: "Fix Verification & Regression Audit",
      desc: "Stage 9 independent rescan comparisons, regression testing invariants, verification policy verdicts, and human sign-off evidence.",
    },
    asset_security_posture: {
      title: "Asset Inventory & Authorization Health",
      desc: "Audit log of all registered digital assets, active authorizations, scan coverage, and per-asset vulnerability distribution.",
    },
  };

  const handleSeverityToggle = (sev: string) => {
    setSelectedSeverities((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev]
    );
  };

  const handleAssetToggle = (assetId: string) => {
    setSelectedAssetIds((prev) =>
      prev.includes(assetId) ? prev.filter((id) => id !== assetId) : [...prev, assetId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) return;

    setSubmitting(true);
    setError(null);

    try {
      const payload = {
        report_type: reportType,
        title: title.trim() || undefined,
        description: description.trim() || undefined,
        format: format,
        asset_ids: selectedAssetIds.length > 0 ? selectedAssetIds : undefined,
        severities: selectedSeverities.length > 0 ? selectedSeverities : undefined,
        include_ai_summary: includeAiSummary,
      };

      const report = await apiClient.post<SecurityReport>(
        `/reports?workspace_id=${activeWorkspace.id}`,
        payload
      );

      router.push(`/reports/${report.id}`);
    } catch (err: any) {
      console.error("Failed to generate report:", err);
      setError(
        err?.error?.message ||
        err?.message ||
        "An unexpected error occurred while generating the security report."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-4xl mx-auto">
          {/* Breadcrumb / Nav */}
          <div className="flex items-center gap-2 text-xs font-mono text-neutral-400">
            <Link href="/reports" className="hover:text-white flex items-center gap-1">
              <ArrowLeft className="h-3.5 w-3.5" />
              Reports Archive
            </Link>
            <span>/</span>
            <span className="text-white">Generate Snapshot</span>
          </div>

          <div className="border-b border-border-subtle pb-4">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-crimson" />
              Generate Security Report Snapshot
            </h1>
            <p className="text-xs text-neutral-400 font-mono mt-1">
              Compile verified findings, deterministic risk scores, and verification evidence into an immutable audit snapshot.
            </p>
          </div>

          {error && (
            <Alert variant="error" title="Report Generation Failed">
              {error}
            </Alert>
          )}

          {/* Security Invariant Alert */}
          <Alert variant="info" title="POINT-IN-TIME IMMUTABILITY GUARANTEE">
            Reports generated in ShadowOps freeze an authoritative snapshot at the moment of creation.
            All metrics are derived strictly from deterministic scan facts. Advisory AI summaries never alter
            deterministic scores or fabricate compliance certifications.
          </Alert>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 1. Select Report Type */}
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader>
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Layers className="h-4 w-4 text-primary-light" />
                  1. Select Report Category
                </CardTitle>
                <CardDescription className="text-xs">
                  Choose the scope and audience for this report
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 pt-0">
                {(Object.keys(reportTypeDescriptions) as ReportType[]).map((typeKey) => {
                  const info = reportTypeDescriptions[typeKey];
                  const isSelected = reportType === typeKey;
                  return (
                    <label
                      key={typeKey}
                      className={`block p-3.5 rounded border transition-colors cursor-pointer ${
                        isSelected
                          ? "bg-neutral-800/80 border-primary text-white"
                          : "bg-neutral-900/40 border-border-subtle text-neutral-300 hover:border-neutral-700"
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="radio"
                          name="report_type"
                          value={typeKey}
                          checked={isSelected}
                          onChange={() => setReportType(typeKey)}
                          className="mt-1"
                        />
                        <div className="space-y-1">
                          <div className="font-semibold text-xs text-white">
                            {info.title}
                          </div>
                          <div className="text-xs text-neutral-400">
                            {info.desc}
                          </div>
                        </div>
                      </div>
                    </label>
                  );
                })}
              </CardContent>
            </Card>

            {/* 2. Metadata & Format */}
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">2. Report Details & Format</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-0">
                <div>
                  <label className="block text-xs font-mono text-neutral-300 mb-1">
                    Custom Title (Optional)
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Q4 Executive Cybersecurity Posture Review"
                    className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-primary"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono text-neutral-300 mb-1">
                    Executive Notes / Context (Optional)
                  </label>
                  <textarea
                    rows={2}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Provide additional context or audit scope notes..."
                    className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-primary"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                  <div>
                    <label className="block text-xs font-mono text-neutral-300 mb-1">
                      Primary Export Format
                    </label>
                    <select
                      value={format}
                      onChange={(e) => setFormat(e.target.value as ReportFormat)}
                      className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-xs text-white focus:outline-none focus:border-primary font-mono"
                    >
                      <option value="pdf">Executive PDF (Styled & Redacted)</option>
                      <option value="json">Structured JSON (Reproducible Data)</option>
                    </select>
                  </div>

                  <div className="flex items-center gap-3 pt-6">
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-mono text-neutral-300">
                      <input
                        type="checkbox"
                        checked={includeAiSummary}
                        onChange={(e) => setIncludeAiSummary(e.target.checked)}
                        className="rounded"
                      />
                      <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                      Include AI Executive Advisory Summary
                    </label>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 3. Scope Filters (Optional) */}
            <Card className="bg-background-secondary border-border-subtle">
              <CardHeader>
                <CardTitle className="text-sm font-semibold">3. Scope & Filtering (Optional)</CardTitle>
                <CardDescription className="text-xs">
                  Leave default to include all authorized assets and severities
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 pt-0">
                {/* Severity Filters */}
                <div>
                  <label className="block text-xs font-mono text-neutral-300 mb-2">
                    Finding Severities Included
                  </label>
                  <div className="flex items-center gap-4">
                    {["critical", "high", "medium", "low"].map((sev) => (
                      <label key={sev} className="flex items-center gap-1.5 cursor-pointer text-xs font-mono text-neutral-300">
                        <input
                          type="checkbox"
                          checked={selectedSeverities.includes(sev)}
                          onChange={() => handleSeverityToggle(sev)}
                        />
                        <span className="capitalize">{sev}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Asset Filters */}
                {assets.length > 0 && (
                  <div>
                    <label className="block text-xs font-mono text-neutral-300 mb-2">
                      Filter by Specific Assets ({selectedAssetIds.length === 0 ? "All Assets Included" : `${selectedAssetIds.length} Selected`})
                    </label>
                    <div className="max-h-36 overflow-y-auto space-y-1.5 border border-border-subtle rounded p-2 bg-neutral-900/50">
                      {assets.map((a) => (
                        <label key={a.id} className="flex items-center gap-2 cursor-pointer text-xs text-neutral-300 hover:text-white">
                          <input
                            type="checkbox"
                            checked={selectedAssetIds.includes(a.id)}
                            onChange={() => handleAssetToggle(a.id)}
                          />
                          <span className="font-semibold">{a.name}</span>
                          <span className="text-[10px] font-mono text-neutral-500">({a.type})</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Submission Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border-subtle">
              <Link href="/reports">
                <Button variant="outline" type="button" disabled={submitting}>
                  Cancel
                </Button>
              </Link>
              <Button variant="primary" type="submit" disabled={submitting} className="gap-2">
                <FileCheck className="h-4 w-4" />
                {submitting ? "Compiling Snapshot..." : "Generate Security Report"}
              </Button>
            </div>
          </form>
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
