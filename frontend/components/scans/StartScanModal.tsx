"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Asset, Scan } from "@/types";
import { apiClient } from "@/lib/api-client";
import { Terminal, ShieldCheck, ShieldAlert, Lock } from "lucide-react";

interface StartScanModalProps {
  isOpen: boolean;
  onClose: () => void;
  asset: Asset | null;
  onScanStarted: (scan: Scan) => void;
}

export function StartScanModal({
  isOpen,
  onClose,
  asset,
  onScanStarted,
}: StartScanModalProps) {
  const [profile, setProfile] = useState<string>("CODE_SECURITY");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!asset) return null;

  const isAuthorized =
    asset.authorization_status === "authorized" ||
    asset.authorization_status === "verified";

  const handleStartScan = async () => {
    if (!isAuthorized) {
      setError("NO AUTHORIZATION -> NO SCAN: Asset lacks verified legal authorization.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const scan = await apiClient.post<Scan>("/scans", {
        asset_id: asset.id,
        scan_profile: profile,
      });

      onScanStarted(scan);
      onClose();
    } catch (err: any) {
      setError(
        err?.error?.message ||
          err?.detail ||
          "Failed to initiate scan. Ensure you have authorized scan permissions."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Engage Controlled Security Scan"
      description={`Initiate defensive security analysis against ${asset.name}.`}
    >
      <div className="space-y-4">
        {/* Authorization Banner */}
        {isAuthorized ? (
          <div className="p-3 rounded bg-emerald-950/20 border border-emerald-800/40 text-xs text-emerald-200/90 flex gap-2.5 items-center">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <div>
              <span className="font-semibold block text-white font-mono">
                AUTHORIZATION VERIFIED
              </span>
              <span>
                Server pre-flight check confirmed legal scanning consent.
              </span>
            </div>
          </div>
        ) : (
          <Alert variant="error" title="SCAN EXECUTION BLOCKED">
            <div className="space-y-1">
              <p>
                <strong>NO AUTHORIZATION → NO SCAN:</strong> The backend security boundary forbids execution on unverified targets.
              </p>
              <p className="font-mono text-[11px]">
                Status: {asset.authorization_status.toUpperCase()}
              </p>
            </div>
          </Alert>
        )}

        {/* Target Details */}
        <div className="space-y-1">
          <label className="text-xs font-medium text-neutral-300">Target Target</label>
          <div className="p-2.5 rounded bg-background border border-border-subtle font-mono text-xs text-neutral-200 flex justify-between items-center">
            <span>{asset.identifier || asset.name}</span>
            <span className="text-[10px] text-neutral-400 uppercase">{asset.type}</span>
          </div>
        </div>

        {/* Scan Profile Selection */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-neutral-300">Analysis Profile</label>
          <div className="grid grid-cols-1 gap-2">
            <div
              onClick={() => setProfile("CODE_SECURITY")}
              className={`p-3 rounded-lg border text-left cursor-pointer transition-colors ${
                profile === "CODE_SECURITY"
                  ? "bg-crimson/10 border-crimson/40 text-white shadow-crimson-glow"
                  : "bg-background-tertiary/40 border-border-subtle text-neutral-300 hover:border-border-muted"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold">CODE_SECURITY (Semgrep Engine)</span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300">
                  AVAILABLE NOW
                </span>
              </div>
              <p className="text-[11px] text-neutral-400 mt-1">
                Static security analysis for SQL injection, secrets, command injection, and crypto vulnerabilities.
              </p>
            </div>

            <div className="p-3 rounded-lg border border-border-subtle bg-background-tertiary/20 text-neutral-500 cursor-not-allowed">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium">STANDARD (Full SAST + Dependency)</span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-neutral-900 border border-neutral-800 text-neutral-500">
                  STAGE 4+
                </span>
              </div>
              <p className="text-[11px] text-neutral-500 mt-1">
                Available in a future scanning stage.
              </p>
            </div>
          </div>
        </div>

        {error && <p className="text-xs text-red-400 font-mono">{error}</p>}

        <div className="flex justify-end gap-2 pt-3 border-t border-border-subtle">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>

          {isAuthorized ? (
            <Button
              type="button"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              onClick={handleStartScan}
            >
              <Terminal className="h-4 w-4" />
              START AUTHORIZED SCAN
            </Button>
          ) : (
            <Button
              type="button"
              variant="danger"
              size="sm"
              disabled
              className="cursor-not-allowed opacity-60"
            >
              <Lock className="h-4 w-4" />
              SCAN BLOCKED
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
