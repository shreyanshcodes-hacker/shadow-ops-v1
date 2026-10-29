"use client";

import React, { useState } from "react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/Table";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { InviteMemberModal } from "@/components/workspace/InviteMemberModal";
import { useWorkspace } from "@/context/WorkspaceContext";
import { Users, UserPlus, Shield, Trash2 } from "lucide-react";

export default function TeamPage() {
  const { activeWorkspace, members, loadingWorkspaces, removeMember } = useWorkspace();
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleRemove = async (memberId: string, email: string) => {
    if (!confirm(`Are you sure you want to remove ${email} from this workspace?`)) return;
    try {
      setDeletingId(memberId);
      await removeMember(memberId);
    } catch (err) {
      console.error("Failed to remove member:", err);
      alert("Failed to remove member. Only owners/admins can perform this action.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">
                Team &amp; Access Control
              </h1>
              <p className="text-xs text-neutral-400 mt-1">
                Collaborators, roles, and administrative privileges for {activeWorkspace?.name || "your workspace"}.
              </p>
            </div>
            {activeWorkspace && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setIsInviteOpen(true)}
              >
                <UserPlus className="h-4 w-4" />
                Invite Member
              </Button>
            )}
          </div>

          {!activeWorkspace ? (
            <EmptyState
              title="No Active Workspace Selected"
              description="Please select or establish a workspace from the sidebar to view team members."
            />
          ) : loadingWorkspaces ? (
            <div className="p-12 flex justify-center">
              <LoadingSpinner size="lg" />
            </div>
          ) : members.length === 0 ? (
            <EmptyState
              icon={<Users className="h-6 w-6 text-crimson" />}
              title="No Team Members Found"
              description="Invite security analysts, engineers, or executive viewers to collaborate."
              actionLabel="Invite First Member"
              onAction={() => setIsInviteOpen(true)}
            />
          ) : (
            <Card variant="bordered">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Collaborator</TableHead>
                    <TableHead>Email Address</TableHead>
                    <TableHead>Workspace Role</TableHead>
                    <TableHead>Joined Date</TableHead>
                    <TableHead>Access Level</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members.map((member) => (
                    <TableRow key={member.id}>
                      <TableCell className="font-medium text-white flex items-center gap-2">
                        <div className="h-7 w-7 rounded-full bg-crimson/20 border border-crimson/60 flex items-center justify-center text-xs font-bold text-white shrink-0">
                          {member.display_name ? member.display_name.slice(0, 2).toUpperCase() : "OP"}
                        </div>
                        <span>{member.display_name || "Security Operator"}</span>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-neutral-300">
                        {member.email}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            member.role === "owner"
                              ? "critical"
                              : member.role === "admin"
                              ? "high"
                              : "default"
                          }
                        >
                          {member.role.toUpperCase()}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-neutral-400">
                        {new Date(member.joined_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-xs text-neutral-400">
                        {member.role === "owner" ? (
                          <span className="text-emerald-400 font-mono">Full Administration</span>
                        ) : member.role === "admin" ? (
                          <span className="text-neutral-300 font-mono">Asset Management</span>
                        ) : (
                          <span className="text-neutral-400 font-mono">Operator</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {member.role !== "owner" && (
                          <button
                            onClick={() => handleRemove(member.id, member.email || "collaborator")}
                            disabled={deletingId === member.id}
                            className="p-1 text-neutral-500 hover:text-crimson transition-colors rounded hover:bg-neutral-800 disabled:opacity-50"
                            title="Remove member"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}

          {/* Invite Member Modal */}
          <InviteMemberModal
            isOpen={isInviteOpen}
            onClose={() => setIsInviteOpen(false)}
          />
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
