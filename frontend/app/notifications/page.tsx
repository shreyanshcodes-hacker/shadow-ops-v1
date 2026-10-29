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
import { apiClient } from "@/lib/api-client";
import { NotificationItem, NotificationListResponse } from "@/types";
import {
  Bell,
  CheckCheck,
  Settings,
  Shield,
  Terminal,
  AlertTriangle,
  Wrench,
  CheckCircle2,
  FileText,
  ExternalLink,
  Clock,
} from "lucide-react";

export default function NotificationsPage() {
  const router = useRouter();
  const { activeWorkspace } = useWorkspace();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("all");

  const fetchNotifications = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    try {
      let query = `/notifications?workspace_id=${activeWorkspace.id}`;
      if (activeTab === "unread") {
        query += "&unread_only=true";
      } else if (activeTab !== "all") {
        query += `&category=${activeTab}`;
      }

      const res = await apiClient.get<NotificationListResponse>(query);
      setNotifications(res.items || []);
      setUnreadCount(res.unread_count || 0);
    } catch (err) {
      console.error("Failed to load notifications:", err);
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, [activeWorkspace, activeTab]);

  const handleMarkAsRead = async (notif: NotificationItem) => {
    if (!activeWorkspace) return;
    try {
      if (!notif.read_at) {
        await apiClient.post(`/notifications/${notif.id}/read?workspace_id=${activeWorkspace.id}`, {});
        setNotifications((prev) =>
          prev.map((item) =>
            item.id === notif.id ? { ...item, read_at: new Date().toISOString() } : item
          )
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      }
      if (notif.link_url) {
        router.push(notif.link_url);
      }
    } catch (err) {
      console.error("Failed to mark as read:", err);
    }
  };

  const handleMarkAllRead = async () => {
    if (!activeWorkspace) return;
    try {
      await apiClient.post(`/notifications/read-all?workspace_id=${activeWorkspace.id}`, {});
      setNotifications((prev) =>
        prev.map((item) => ({ ...item, read_at: item.read_at || new Date().toISOString() }))
      );
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all as read:", err);
    }
  };

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case "scans":
        return <Terminal className="h-4 w-4 text-cyan-400" />;
      case "findings":
        return <AlertTriangle className="h-4 w-4 text-amber-400" />;
      case "remediation":
        return <Wrench className="h-4 w-4 text-indigo-400" />;
      case "verification":
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case "reports":
        return <FileText className="h-4 w-4 text-blue-400" />;
      case "risk":
        return <Shield className="h-4 w-4 text-crimson" />;
      default:
        return <Bell className="h-4 w-4 text-neutral-400" />;
    }
  };

  const tabs = [
    { id: "all", label: "All" },
    { id: "unread", label: `Unread (${unreadCount})` },
    { id: "scans", label: "Scans" },
    { id: "findings", label: "Findings" },
    { id: "remediation", label: "Remediation" },
    { id: "verification", label: "Verification" },
    { id: "reports", label: "Reports" },
    { id: "risk", label: "Risk" },
  ];

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border-subtle pb-5">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  <Bell className="h-5 w-5 text-crimson" />
                  Security Notification Center
                </h1>
                {unreadCount > 0 && (
                  <Badge variant="critical">
                    {unreadCount} Unread
                  </Badge>
                )}
              </div>
              <p className="text-xs text-neutral-400 mt-1">
                Real-time security alerts, remediation authorizations, verification outcomes, and automated workflow events.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleMarkAllRead}
                disabled={loading || unreadCount === 0}
                className="text-xs flex items-center gap-1.5"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all as read
              </Button>

              <Link href="/settings/notifications">
                <Button variant="ghost" size="sm" className="text-xs flex items-center gap-1.5 border border-border-subtle">
                  <Settings className="h-3.5 w-3.5" />
                  Preferences
                </Button>
              </Link>
            </div>
          </div>

          {/* Category Tabs */}
          <div className="flex flex-wrap gap-1 border-b border-border-subtle pb-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  activeTab === tab.id
                    ? "bg-crimson/20 text-white border border-crimson/50"
                    : "text-neutral-400 hover:text-white hover:bg-background-tertiary"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Notifications List */}
          {loading ? (
            <div className="text-center py-16 text-neutral-500 font-mono text-xs">
              Loading security notifications...
            </div>
          ) : notifications.length === 0 ? (
            <EmptyState
              title="No Notifications Found"
              description="You have no notifications matching the selected filter."
              actionLabel="Configure Notification Preferences"
              onAction={() => router.push("/settings/notifications")}
            />
          ) : (
            <div className="space-y-2.5">
              {notifications.map((notif) => {
                const isUnread = !notif.read_at;
                return (
                  <div
                    key={notif.id}
                    onClick={() => handleMarkAsRead(notif)}
                    className={`p-4 rounded-lg border transition-all cursor-pointer flex items-start justify-between gap-4 ${
                      isUnread
                        ? "bg-background-secondary/90 border-crimson/30 hover:border-crimson/60 shadow-sm"
                        : "bg-background-secondary/40 border-border-subtle hover:bg-background-tertiary/40"
                    }`}
                  >
                    <div className="flex items-start gap-3.5 min-w-0">
                      <div className="p-2 rounded bg-background border border-border-subtle shrink-0 mt-0.5">
                        {getCategoryIcon(notif.category)}
                      </div>
                      <div className="space-y-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-sm font-semibold truncate ${isUnread ? "text-white" : "text-neutral-300"}`}>
                            {notif.title}
                          </span>
                          <Badge variant="outline" className="text-[10px] uppercase font-mono">
                            {notif.category}
                          </Badge>
                          {isUnread && (
                            <span className="h-1.5 w-1.5 rounded-full bg-crimson" />
                          )}
                        </div>
                        <p className="text-xs text-neutral-400 leading-relaxed">
                          {notif.message}
                        </p>
                        <div className="flex items-center gap-3 text-[11px] font-mono text-neutral-500 pt-1">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(notif.created_at).toLocaleString()}
                          </span>
                          <span>Channels: {notif.channels.join(", ")}</span>
                        </div>
                      </div>
                    </div>

                    {notif.link_url && (
                      <div className="shrink-0 text-neutral-500 hover:text-white pt-1">
                        <ExternalLink className="h-4 w-4" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
