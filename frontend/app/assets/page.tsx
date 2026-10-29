"use client";

import React, { useEffect, useState } from "react";
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
import { Asset } from "@/types";
import { Server, Plus, ShieldCheck, ShieldAlert, ExternalLink } from "lucide-react";
import { AddAssetModal } from "@/components/assets/AddAssetModal";
import { AuthorizeAssetModal } from "@/components/assets/AuthorizeAssetModal";
import { StartScanModal } from "@/components/scans/StartScanModal";

export default function AssetsPage() {
  const { activeWorkspace } = useWorkspace();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedAssetForAuth, setSelectedAssetForAuth] = useState<Asset | null>(null);
  const [selectedAssetForScan, setSelectedAssetForScan] = useState<Asset | null>(null);

  const fetchAssets = async () => {
    if (!activeWorkspace) {
      setAssets([]);
      return;
    }
    setLoading(true);
    try {
      const data = await apiClient.get<Asset[]>(`/workspaces/${activeWorkspace.id}/assets`);
      setAssets(data);
    } catch (err) {
      console.error("Failed to load assets:", err);
      setAssets([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, [activeWorkspace]);

  const handleAssetCreated = (newAsset: Asset) => {
    setAssets((prev) => [newAsset, ...prev]);
  };

  const handleAssetAuthorized = (updatedAsset: Asset) => {
    setAssets((prev) =>
      prev.map((a) => (a.id === updatedAsset.id ? updatedAsset : a))
    );
  };

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Assets &amp; Security Boundary
              </h1>
              <p className="text-xs text-neutral-400 mt-1">
                Authorized repositories, cloud services, and target scopes registered in {activeWorkspace?.name || "your workspace"}.
              </p>
            </div>
            {activeWorkspace && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setShowAddModal(true)}
              >
                <Plus className="h-4 w-4" />
                Register Asset
              </Button>
            )}
          </div>

          {!activeWorkspace ? (
            <EmptyState
              title="No Active Workspace Selected"
              description="Please select or establish a workspace from the sidebar to view registered assets."
            />
          ) : loading ? (
            <div className="p-12 flex justify-center">
              <LoadingSpinner size="lg" />
            </div>
          ) : assets.length === 0 ? (
            <EmptyState
              icon={<Server className="h-6 w-6 text-crimson" />}
              title="No Monitored Assets Found"
              description="Onboard your first repository or application target to configure authorization proofs and security policies."
              actionLabel="Onboard Target Asset"
              onAction={() => setShowAddModal(true)}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Asset Name</TableHead>
                  <TableHead>Identifier</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Environment</TableHead>
                  <TableHead>Criticality</TableHead>
                  <TableHead>Authorization Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {assets.map((asset) => (
                  <TableRow key={asset.id}>
                    <TableCell className="font-medium text-white">
                      {asset.name}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-neutral-300">
                      {asset.identifier || "--"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{asset.type.toUpperCase()}</Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-neutral-300 capitalize">
                        {asset.environment}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          asset.criticality === "critical"
                            ? "critical"
                            : asset.criticality === "high"
                            ? "high"
                            : "default"
                        }
                      >
                        {asset.criticality.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {asset.authorization_status === "authorized" ? (
                        <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-xs">
                          <ShieldCheck className="h-4 w-4" />
                          <span>AUTHORIZED</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-amber-400 font-mono text-xs">
                          <ShieldAlert className="h-4 w-4" />
                          <span className="uppercase">{asset.authorization_status}</span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {asset.authorization_status !== "authorized" && asset.authorization_status !== "verified" ? (
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setSelectedAssetForAuth(asset)}
                          >
                            Verify Consent
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            disabled
                            className="cursor-not-allowed opacity-50"
                            title="NO AUTHORIZATION -> NO SCAN"
                          >
                            Scan Blocked
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={() => setSelectedAssetForScan(asset)}
                          >
                            Start Scan
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedAssetForAuth(asset)}
                          >
                            Details
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Add Asset Modal */}
          {activeWorkspace && (
            <AddAssetModal
              isOpen={showAddModal}
              onClose={() => setShowAddModal(false)}
              workspaceId={activeWorkspace.id}
              onAssetCreated={handleAssetCreated}
            />
          )}

          {/* Authorize Asset Modal */}
          <AuthorizeAssetModal
            isOpen={Boolean(selectedAssetForAuth)}
            onClose={() => setSelectedAssetForAuth(null)}
            asset={selectedAssetForAuth}
            onAuthorized={handleAssetAuthorized}
          />

          {/* Start Scan Modal */}
          <StartScanModal
            isOpen={Boolean(selectedAssetForScan)}
            onClose={() => setSelectedAssetForScan(null)}
            asset={selectedAssetForScan}
            onScanStarted={() => {
              window.location.href = "/scans";
            }}
          />
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
