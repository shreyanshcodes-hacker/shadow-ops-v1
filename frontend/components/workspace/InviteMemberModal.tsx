"use client";

import React, { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useWorkspace } from "@/context/WorkspaceContext";
import { UserPlus, Shield, AlertCircle } from "lucide-react";

interface InviteMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function InviteMemberModal({ isOpen, onClose }: InviteMemberModalProps) {
  const { activeWorkspace, inviteMember } = useWorkspace();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmed = email.trim().toLowerCase();
    if (!trimmed || !trimmed.includes("@")) {
      setError("Please enter a valid email address.");
      return;
    }

    try {
      setIsSubmitting(true);
      await inviteMember(trimmed, role);
      setEmail("");
      setRole("member");
      onClose();
    } catch (err: any) {
      console.error("Invite member failed:", err);
      setError(err?.message || "Failed to invite member. Check admin privileges.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Invite Team Collaborator"
      description={`Grant access to workspace "${activeWorkspace?.name || "your workspace"}".`}
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        {error && (
          <div className="p-3 rounded-lg bg-crimson/10 border border-crimson/30 text-crimson text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-mono text-neutral-300 mb-1.5">
            Collaborator Email Address
          </label>
          <Input
            type="email"
            placeholder="security-analyst@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isSubmitting}
            required
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-xs font-mono text-neutral-300 mb-1.5">
            Designated Role &amp; Access Level
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            disabled={isSubmitting}
            className="w-full px-3 py-2 rounded-md bg-neutral-900 border border-neutral-700 text-neutral-200 text-xs font-mono focus:outline-none focus:border-crimson"
          >
            <option value="admin">ADMIN — Asset management, scans, team invitations</option>
            <option value="member">MEMBER — Operator, scans, remediation inspection</option>
            <option value="viewer">VIEWER — Read-only dashboard, reports, security postures</option>
          </select>
        </div>

        <div className="p-3 rounded-lg bg-neutral-900/60 border border-border-subtle flex items-start gap-2.5 text-xs text-neutral-400">
          <Shield className="h-4 w-4 text-crimson shrink-0 mt-0.5" />
          <p>
            Invited members gain access to assets, scans, and security findings scoped strictly to this workspace.
          </p>
        </div>

        <div className="flex justify-end gap-3 pt-3 border-t border-border-subtle">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={isSubmitting}
            className="gap-2"
          >
            <UserPlus className="h-4 w-4" />
            {isSubmitting ? "Inviting..." : "Send Invitation"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
