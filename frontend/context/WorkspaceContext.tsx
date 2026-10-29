"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { Workspace, WorkspaceMember } from "@/types";
import { useAuth } from "./AuthContext";

interface WorkspaceContextType {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  members: WorkspaceMember[];
  loadingWorkspaces: boolean;
  setActiveWorkspace: (ws: Workspace) => void;
  createWorkspace: (name: string, description?: string) => Promise<Workspace>;
  inviteMember: (email: string, role: string) => Promise<WorkspaceMember>;
  removeMember: (memberId: string) => Promise<void>;
  refreshWorkspaces: () => Promise<void>;
  refreshMembers: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

const ACTIVE_WS_STORAGE_KEY = "shadowops_active_workspace";

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspaceState] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState<boolean>(true);

  const refreshMembers = useCallback(async () => {
    if (!activeWorkspace) {
      setMembers([]);
      return;
    }
    try {
      const data = await apiClient.get<WorkspaceMember[]>(`/workspaces/${activeWorkspace.id}/members`);
      setMembers(data);
    } catch (err) {
      console.error("Failed to load workspace members:", err);
      setMembers([]);
    }
  }, [activeWorkspace]);

  const refreshWorkspaces = useCallback(async () => {
    if (!isAuthenticated) {
      setWorkspaces([]);
      setActiveWorkspaceState(null);
      setMembers([]);
      setLoadingWorkspaces(false);
      return;
    }

    setLoadingWorkspaces(true);
    try {
      const list = await apiClient.get<Workspace[]>("/workspaces");
      setWorkspaces(list);

      // Restore stored workspace if still accessible
      const savedId = typeof window !== "undefined" ? localStorage.getItem(ACTIVE_WS_STORAGE_KEY) : null;
      let matched = list.find((w) => w.id === savedId);
      if (!matched && list.length > 0) {
        matched = list[0];
      }

      if (matched) {
        setActiveWorkspaceState(matched);
        if (typeof window !== "undefined") {
          localStorage.setItem(ACTIVE_WS_STORAGE_KEY, matched.id);
        }
      } else {
        setActiveWorkspaceState(null);
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
      setWorkspaces([]);
      setActiveWorkspaceState(null);
    } finally {
      setLoadingWorkspaces(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refreshWorkspaces();
  }, [refreshWorkspaces]);

  useEffect(() => {
    if (activeWorkspace) {
      refreshMembers();
    }
  }, [activeWorkspace, refreshMembers]);

  const setActiveWorkspace = (ws: Workspace) => {
    setActiveWorkspaceState(ws);
    if (typeof window !== "undefined") {
      localStorage.setItem(ACTIVE_WS_STORAGE_KEY, ws.id);
    }
  };

  const createWorkspace = async (name: string, description?: string): Promise<Workspace> => {
    const newWs = await apiClient.post<Workspace>("/workspaces", {
      name,
      description,
    });
    setWorkspaces((prev) => [newWs, ...prev]);
    setActiveWorkspace(newWs);
    return newWs;
  };

  const inviteMember = async (email: string, role: string): Promise<WorkspaceMember> => {
    if (!activeWorkspace) throw new Error("No active workspace selected");
    const newMember = await apiClient.post<WorkspaceMember>(`/workspaces/${activeWorkspace.id}/members`, {
      email,
      role,
    });
    setMembers((prev) => [...prev, newMember]);
    return newMember;
  };

  const removeMember = async (memberId: string): Promise<void> => {
    if (!activeWorkspace) throw new Error("No active workspace selected");
    await apiClient.delete(`/workspaces/${activeWorkspace.id}/members/${memberId}`);
    setMembers((prev) => prev.filter((m) => m.id !== memberId));
  };

  const value: WorkspaceContextType = {
    workspaces,
    activeWorkspace,
    members,
    loadingWorkspaces,
    setActiveWorkspace,
    createWorkspace,
    inviteMember,
    removeMember,
    refreshWorkspaces,
    refreshMembers,
  };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace(): WorkspaceContextType {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return context;
}
