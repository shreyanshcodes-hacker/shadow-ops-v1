"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { Scan } from "@/types";
import { Terminal, Shield, ArrowRight, Play, AlertCircle } from "lucide-react";

export default function ScansPage() {
  const { activeWorkspace } = useWorkspace();
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchScans = async () => {
    if (!activeWorkspace) {
      setScans([]);
      return;
    }
    setLoading(true);
    try {
      const data = await apiClient.get<Scan[]>(`/scans?workspace_id=${activeWorkspace.id}`);
      setScans(data);
    } catch (err) {
      console.error("Failed to load scans:", err);
      setScans([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, [activeWorkspace]);

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Security Scans &amp; Runs
              </h1>
              <p className="text-xs text-neutral-400 mt-1">
                Controlled static code analysis runs executed against authorized repositories.
              </p>
            </div>
            <Link href="/assets">
              <Button variant="primary" size="sm">
                <Play className="h-4 w-4" />
                Launch New Scan
              </Button>
            </Link>
          </div>

          {!activeWorkspace ? (
            <EmptyState
              title="No Active Workspace Selected"
              description="Please select or establish a workspace from the sidebar to view security scans."
            />
          ) : loading ? (
            <div className="p-12 flex justify-center">
              <LoadingSpinner size="lg" />
            </div>
          ) : scans.length === 0 ? (
            <EmptyState
              icon={<Terminal className="h-6 w-6 text-crimson" />}
              title="No Security Scans Executed Yet"
              description="Head to the Assets page, verify authorization, and engage your first Semgrep static analysis run."
              actionLabel="Go to Assets"
              onAction={() => window.location.href = "/assets"}
            />
          ) : (
            <Card variant="bordered">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scan ID</TableHead>
                    <TableHead>Profile</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Findings Summary</TableHead>
                    <TableHead>Started Time</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {scans.map((scan) => (
                    <TableRow key={scan.id}>
                      <TableCell className="font-mono text-xs text-white">
                        {scan.id.slice(0, 8)}...
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{scan.scan_profile}</Badge>
                      </TableCell>
                      <TableCell>
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
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2 font-mono text-xs">
                          <span className="text-white font-semibold">
                            {scan.summary.total_findings} total
                          </span>
                          {scan.summary.critical > 0 && (
                            <span className="text-red-400 font-semibold">
                              ({scan.summary.critical} crit)
                            </span>
                          )}
                          {scan.summary.high > 0 && (
                            <span className="text-orange-400">
                              ({scan.summary.high} high)
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-neutral-400">
                        {new Date(scan.triggered_at).toLocaleTimeString()}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-neutral-400">
                        {scan.duration_ms ? `${scan.duration_ms} ms` : "--"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link href={`/scans/${scan.id}`}>
                          <Button variant="secondary" size="sm" className="gap-1.5">
                            <span>Inspect</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
