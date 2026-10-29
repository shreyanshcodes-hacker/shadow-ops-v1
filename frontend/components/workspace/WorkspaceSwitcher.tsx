"use client";

import React, { useState } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { ChevronDown, Check, Plus, Building2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export function WorkspaceSwitcher() {
  const { workspaces, activeWorkspace, setActiveWorkspace, createWorkspace } = useWorkspace();
  const [isOpen, setIsOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [newWsDesc, setNewWsDesc] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      await createWorkspace(newWsName.trim(), newWsDesc.trim() || undefined);
      setShowCreateModal(false);
      setNewWsName("");
      setNewWsDesc("");
      setIsOpen(false);
    } catch (err: any) {
      setError(err?.error?.message || "Failed to create workspace. Try another name.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between p-2 rounded-lg bg-background-tertiary/60 border border-border-subtle hover:border-border-muted transition-colors text-left"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="h-6 w-6 rounded bg-neutral-800 border border-border-muted flex items-center justify-center shrink-0">
              <Building2 className="h-3.5 w-3.5 text-neutral-300" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-[10px] uppercase font-mono text-neutral-400 leading-none mb-0.5">Workspace</span>
              <span className="text-xs font-semibold text-white truncate max-w-[130px]">
                {activeWorkspace ? activeWorkspace.name : "Select Workspace"}
              </span>
            </div>
          </div>
          <ChevronDown className="h-4 w-4 text-neutral-400 shrink-0" />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 z-50 rounded-lg bg-background-elevated border border-border-muted shadow-2xl p-1.5 space-y-1">
            <div className="max-h-48 overflow-y-auto space-y-0.5">
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => {
                    setActiveWorkspace(ws);
                    setIsOpen(false);
                  }}
                  className="w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs text-neutral-200 hover:bg-background-tertiary transition-colors text-left"
                >
                  <span className="truncate">{ws.name}</span>
                  {activeWorkspace?.id === ws.id && (
                    <Check className="h-3.5 w-3.5 text-crimson-light shrink-0" />
                  )}
                </button>
              ))}
            </div>

            <div className="pt-1 border-t border-border-subtle">
              <button
                onClick={() => {
                  setIsOpen(false);
                  setShowCreateModal(true);
                }}
                className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded text-xs font-medium text-crimson hover:bg-crimson/10 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Create Workspace</span>
              </button>
            </div>
          </div>
        )}
      </div>

      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Security Workspace"
        description="Establish an isolated multi-tenant perimeter for security operations."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Workspace Name"
            placeholder="e.g. Acme Production Security"
            value={newWsName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewWsName(e.target.value)}
            required
            autoFocus
          />

          <Input
            label="Description (Optional)"
            placeholder="Brief description of this environment"
            value={newWsDesc}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewWsDesc(e.target.value)}
          />

          {error && <p className="text-xs text-red-400 font-mono">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              isLoading={isSubmitting}
              disabled={!newWsName.trim()}
            >
              Create Workspace
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
