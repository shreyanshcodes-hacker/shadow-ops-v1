"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { apiClient } from "@/lib/api-client";
import { Asset, AssetAuthorization } from "@/types";
import { ShieldCheck, AlertTriangle } from "lucide-react";

interface AuthorizeAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: Asset | null;
  onAuthorized: (updatedAsset: Asset) => void;
}

export function AuthorizeAssetModal({
  isOpen,
  onClose,
  asset,
  onAuthorized,
}: AuthorizeAssetModalProps) {
  const [authType, setAuthType] = useState("ownership");
  const [scope, setScope] = useState("full_scan");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!asset) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        authorization_type: authType,
        authorization_scope: scope,
        authorization_reference: reference.trim() || undefined,
        notes: notes.trim() || undefined,
      };

      await apiClient.post<AssetAuthorization>(
        `/assets/${asset.id}/authorization`,
        payload
      );

      // Mutate local asset authorization status to authorized
      const updated: Asset = {
        ...asset,
        authorization_status: "authorized",
      };
      onAuthorized(updated);
      onClose();
    } catch (err: any) {
      setError(
        err?.error?.message ||
          "Failed to record authorization. Ensure you are an OWNER or ADMIN of this workspace."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Verify Asset Authorization"
      description={`Record explicit security authorization for ${asset.name}.`}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="p-3 rounded bg-amber-950/20 border border-amber-800/40 text-xs text-amber-200/90 flex gap-2.5 items-start">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            <strong>NO AUTHORIZATION → NO SCAN:</strong> The backend strictly forbids security scans on unverified targets. By proceeding, you attest legal authorization to perform automated security testing against this asset.
          </span>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-neutral-300">Target Identifier</label>
          <div className="p-2 rounded bg-background border border-border-subtle font-mono text-xs text-neutral-200">
            {asset.identifier || asset.name}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-medium text-neutral-300">Proof Type</label>
            <select
              value={authType}
              onChange={(e) => setAuthType(e.target.value)}
              className="flex h-9 w-full rounded-md border border-border-subtle bg-background px-3 py-1 text-sm text-neutral-100 focus:outline-none focus:ring-1 focus:ring-crimson"
            >
              <option value="ownership">Repository / Domain Ownership</option>
              <option value="dns_token">DNS TXT Verification</option>
              <option value="http_token">HTTP Well-Known File</option>
              <option value="admin_override">Executive Dual-Custody Approval</option>
            </select>
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-medium text-neutral-300">Testing Scope</label>
            <select
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              className="flex h-9 w-full rounded-md border border-border-subtle bg-background px-3 py-1 text-sm text-neutral-100 focus:outline-none focus:ring-1 focus:ring-crimson"
            >
              <option value="full_scan">Full Depth Scan (SAST + DAST)</option>
              <option value="sast_only">Static Code Analysis Only</option>
              <option value="passive_only">Passive Perimeter Recon Only</option>
            </select>
          </div>
        </div>

        <Input
          label="Verification Reference / Token"
          placeholder="e.g. DNS TXT record value or internal ticket ID"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />

        <Input
          label="Attestation Notes"
          placeholder="e.g. Authorized under Security Policy RFC-441"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />

        {error && <p className="text-xs text-red-400 font-mono">{error}</p>}

        <div className="flex justify-end gap-2 pt-2 border-t border-border-subtle">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            isLoading={isSubmitting}
          >
            <ShieldCheck className="h-4 w-4" />
            Sign &amp; Verify Authorization
          </Button>
        </div>
      </form>
    </Modal>
  );
}
