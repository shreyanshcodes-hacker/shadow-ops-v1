"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { apiClient } from "@/lib/api-client";
import { Asset, AssetCriticality, AssetType } from "@/types";

interface AddAssetModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
  onAssetCreated: (asset: Asset) => void;
}

export function AddAssetModal({
  isOpen,
  onClose,
  workspaceId,
  onAssetCreated,
}: AddAssetModalProps) {
  const [name, setName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [type, setType] = useState<AssetType>("repository");
  const [environment, setEnvironment] = useState("production");
  const [criticality, setCriticality] = useState<AssetCriticality>("high");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !identifier.trim()) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name: name.trim(),
        type,
        identifier: identifier.trim(),
        criticality,
        connection_config: {
          identifier: identifier.trim(),
          environment,
          description: description.trim() || undefined,
        },
        tags: [environment, type],
      };

      const created = await apiClient.post<Asset>(
        `/workspaces/${workspaceId}/assets`,
        payload
      );

      onAssetCreated(created);
      onClose();
      // Reset form
      setName("");
      setIdentifier("");
      setDescription("");
    } catch (err: any) {
      setError(
        err?.error?.message ||
          "Failed to onboard asset. Ensure identifier does not target prohibited private/SSRF IPs."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Onboard Target Asset"
      description="Register an authorized repository or system under the active workspace perimeter."
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Asset Name"
          placeholder="e.g. Core Payment Service"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        <Input
          label="Identifier / Target URL"
          placeholder="e.g. github.com/acme/payment-service or https://api.acme.com"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
        />

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-medium text-neutral-300 tracking-wide">
              Asset Type
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as AssetType)}
              className="flex h-9 w-full rounded-md border border-border-subtle bg-background px-3 py-1 text-sm text-neutral-100 focus:outline-none focus:ring-1 focus:ring-crimson"
            >
              <option value="repository">Repository (Codebase)</option>
              <option value="api">API Endpoint</option>
              <option value="application">Web Application</option>
              <option value="infrastructure">Infrastructure Host</option>
            </select>
          </div>

          <div className="flex flex-col space-y-1.5">
            <label className="text-xs font-medium text-neutral-300 tracking-wide">
              Environment
            </label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="flex h-9 w-full rounded-md border border-border-subtle bg-background px-3 py-1 text-sm text-neutral-100 focus:outline-none focus:ring-1 focus:ring-crimson"
            >
              <option value="production">Production</option>
              <option value="staging">Staging</option>
              <option value="development">Development</option>
            </select>
          </div>
        </div>

        <div className="flex flex-col space-y-1.5">
          <label className="text-xs font-medium text-neutral-300 tracking-wide">
            Criticality Tier
          </label>
          <select
            value={criticality}
            onChange={(e) => setCriticality(e.target.value as AssetCriticality)}
            className="flex h-9 w-full rounded-md border border-border-subtle bg-background px-3 py-1 text-sm text-neutral-100 focus:outline-none focus:ring-1 focus:ring-crimson"
          >
            <option value="critical">Critical (Tier 0 - Crown Jewels)</option>
            <option value="high">High (Customer Data / Financial)</option>
            <option value="medium">Medium (Internal Tooling)</option>
            <option value="low">Low (Non-sensitive / Static)</option>
          </select>
        </div>

        <Input
          label="Description (Optional)"
          placeholder="Business context and security notes"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
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
            disabled={!name.trim() || !identifier.trim()}
          >
            Onboard Asset
          </Button>
        </div>
      </form>
    </Modal>
  );
}
