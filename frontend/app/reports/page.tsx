"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient, downloadFile } from "@/lib/api-client";
import { SecurityReport, ReportListResponse, ReportType } from "@/types";
import {
  FileText,
  Plus,
  Download,
  Eye,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Filter,
  Shield,
  FileCheck,
} from "lucide-react";

export default function ReportsListPage() {
  const router = useRouter();
  const { activeWorkspace } = useWorkspace();
  const [reports, setReports] = useState<SecurityReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("all");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const fetchReports = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    try {
      const typeParam = activeTab !== "all" ? `&report_type=${activeTab}` : "";
      const res = await apiClient.get<ReportListResponse>(
        `/reports?workspace_id=${activeWorkspace.id}${typeParam}`
      );
      setReports(res.items || []);
    } catch (err) {
      console.error("Failed to load reports:", err);
      setReports([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [activeWorkspace, activeTab]);

  const handleDownload = async (reportId: string, format: "pdf" | "json") => {
    if (!activeWorkspace) return;
    setDownloadingId(`${reportId}-${format}`);
    try {
      await downloadFile(
        `/reports/${reportId}/download?workspace_id=${activeWorkspace.id}&format=${format}`
      );
    } catch (err) {
      console.error(`Failed to download ${format}:`, err);
      alert(`Download failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setDownloadingId(null);
    }
  };

  const getBadgeVariant = (type: string) => {
    switch (type) {
      case "executive_summary":
        return "info";
      case "technical_vulnerability":
        return "critical";
      case "remediation_progress":
        return "medium";
      case "verification_regression":
        return "success";
      case "asset_security_posture":
        return "low";
      default:
        return "default";
    }
  };

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border-subtle pb-5">
            <div>
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded bg-primary/10 border border-primary/30 flex items-center justify-center text-primary-light">
                  <FileText className="h-4 w-4" />
                </div>
                <div>
                  <h1 className="text-xl font-bold tracking-tight text-white">Security Reports & Compliance</h1>
                  <p className="text-xs text-neutral-400 font-mono">
                    Immutable, point-in-time posture snapshots grounded in verified scanner facts
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Link href="/reports/new">
                <Button variant="primary" size="sm" className="gap-2">
                  <Plus className="h-4 w-4" />
                  Generate Report
                </Button>
              </Link>
            </div>
          </div>

          {/* Type Filter Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto border-b border-border-subtle pb-2">
            {[
              { id: "all", label: "All Reports" },
              { id: "executive_summary", label: "Executive Summary" },
              { id: "technical_vulnerability", label: "Technical Vulnerabilities" },
              { id: "remediation_progress", label: "Remediation Progress" },
              { id: "verification_regression", label: "Fix Verifications" },
              { id: "asset_security_posture", label: "Asset Posture" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded text-xs font-mono transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-neutral-800 text-white border border-neutral-700 font-semibold"
                    : "text-neutral-400 hover:text-white hover:bg-neutral-900/50"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Reports Table / List */}
          {loading ? (
            <div className="p-12 text-center text-sm font-mono text-neutral-400">
              Loading security reports...
            </div>
          ) : reports.length === 0 ? (
            <EmptyState
              icon={<FileCheck className="h-8 w-8 text-neutral-500" />}
              title="No Security Reports Generated"
              description="Create an immutable, audit-ready security report snapshot to export executive summaries, technical vulnerabilities, or verification audits."
              actionLabel="Generate First Report"
              onAction={() => router.push("/reports/new")}
            />
          ) : (
            <div className="space-y-3">
              {reports.map((report) => (
                <Card key={report.id} className="bg-background-secondary border-border-subtle hover:border-neutral-700 transition-colors">
                  <CardContent className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant={getBadgeVariant(report.report_type)}>
                          {report.report_type.replace(/_/g, " ").toUpperCase()}
                        </Badge>
                        <Badge variant={report.status === "completed" ? "success" : "default"}>
                          {report.status.toUpperCase()}
                        </Badge>
                        {report.completeness_status === "PARTIAL" && (
                          <Badge variant="high" title="Report contains partial coverage or un-scanned perimeters">
                            PARTIAL COVERAGE
                          </Badge>
                        )}
                        <span className="text-[11px] font-mono text-neutral-400">
                          Cutoff: {new Date(report.data_cutoff_at).toLocaleString("en-US", { timeZone: "UTC" })} UTC
                        </span>
                      </div>

                      <h3 className="font-semibold text-sm text-white truncate">
                        {report.title}
                      </h3>
                      {report.description && (
                        <p className="text-xs text-neutral-400 line-clamp-1">
                          {report.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-[11px] font-mono text-neutral-400 pt-1">
                        <span>Author: {report.generated_by}</span>
                        <span>Format: {report.format.toUpperCase()}</span>
                        <span>Schema: {report.schema_version}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start md:self-center shrink-0">
                      <Link href={`/reports/${report.id}`}>
                        <Button variant="outline" size="sm" className="gap-1.5 text-xs">
                          <Eye className="h-3.5 w-3.5" />
                          View
                        </Button>
                      </Link>

                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={downloadingId === `${report.id}-pdf`}
                        onClick={() => handleDownload(report.id, "pdf")}
                        className="gap-1.5 text-xs text-crimson-light hover:text-white"
                        title="Export as Executive PDF"
                      >
                        <Download className="h-3.5 w-3.5" />
                        {downloadingId === `${report.id}-pdf` ? "Downloading..." : "PDF"}
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={downloadingId === `${report.id}-json`}
                        onClick={() => handleDownload(report.id, "json")}
                        className="gap-1.5 text-xs text-neutral-300 hover:text-white"
                        title="Export as Raw Structured JSON"
                      >
                        <Download className="h-3.5 w-3.5" />
                        {downloadingId === `${report.id}-json` ? "Downloading..." : "JSON"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
