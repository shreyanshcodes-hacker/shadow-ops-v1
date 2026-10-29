"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import { NotificationPreferences } from "@/types";
import {
  Bell,
  ArrowLeft,
  Mail,
  Shield,
  Save,
  CheckCircle2,
  AlertTriangle,
  Info,
} from "lucide-react";

export default function NotificationSettingsPage() {
  const { activeWorkspace } = useWorkspace();
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPreferences = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    try {
      const res = await apiClient.get<NotificationPreferences>(
        `/notifications/preferences?workspace_id=${activeWorkspace.id}`
      );
      setPreferences(res);
    } catch (err) {
      console.error("Failed to load preferences:", err);
      setError("Failed to load notification preferences.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreferences();
  }, [activeWorkspace]);

  const handleToggleCategory = (category: string) => {
    if (!preferences) return;
    setPreferences({
      ...preferences,
      categories: {
        ...preferences.categories,
        [category]: !preferences.categories[category],
      },
    });
  };

  const handleToggleChannel = (channel: string) => {
    if (!preferences) return;
    setPreferences({
      ...preferences,
      channels: {
        ...preferences.channels,
        [channel]: !preferences.channels[channel],
      },
    });
  };

  const handleSave = async () => {
    if (!activeWorkspace || !preferences) return;
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const res = await apiClient.put<NotificationPreferences>(
        `/notifications/preferences?workspace_id=${activeWorkspace.id}`,
        {
          categories: preferences.categories,
          channels: preferences.channels,
          min_severity: preferences.min_severity,
        }
      );
      setPreferences(res);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to update preferences:", err);
      setError("Failed to save preferences.");
    } finally {
      setSaving(false);
    }
  };

  const categoryLabels: Record<string, { label: string; desc: string }> = {
    scans: {
      label: "Scans & Scanner Execution",
      desc: "Completed and failed scan jobs across authorized repositories and APIs.",
    },
    findings: {
      label: "Vulnerability Findings",
      desc: "Newly identified vulnerabilities, severity elevations, and status updates.",
    },
    remediation: {
      label: "Remediation & Approval Requests",
      desc: "AI patch proposals, validation failures, and governance authorization requests.",
    },
    verification: {
      label: "Fix Verification & Regression",
      desc: "Independent rescan results, regression alerts, and human review gates.",
    },
    reports: {
      label: "Security Reports",
      desc: "Generated executive summaries, technical reports, and PDF download readiness.",
    },
    risk: {
      label: "Risk Score & Critical Thresholds",
      desc: "Significant risk score changes and attack path emergence across assets.",
    },
  };

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="space-y-6 max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border-subtle pb-5">
            <div className="flex items-center gap-3">
              <Link href="/notifications">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-neutral-400 hover:text-white">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  <Bell className="h-5 w-5 text-crimson" />
                  Notification Preferences
                </h1>
                <p className="text-xs text-neutral-400 mt-1">
                  Configure alert routing, delivery channels, and severity filters for workspace events.
                </p>
              </div>
            </div>

            <Button
              onClick={handleSave}
              disabled={saving || loading || !preferences}
              size="sm"
              className="text-xs flex items-center gap-1.5 bg-crimson hover:bg-crimson-light text-white"
            >
              <Save className="h-3.5 w-3.5" />
              {saving ? "Saving..." : "Save Preferences"}
            </Button>
          </div>

          {saveSuccess && (
            <Alert variant="success" className="text-xs">
              Notification preferences saved successfully.
            </Alert>
          )}

          {error && (
            <Alert variant="error" className="text-xs">
              {error}
            </Alert>
          )}

          {loading || !preferences ? (
            <div className="text-center py-16 text-neutral-500 font-mono text-xs">
              Loading preferences...
            </div>
          ) : (
            <div className="space-y-6">
              {/* Delivery Channels */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Mail className="h-4 w-4 text-cyan-400" />
                    Delivery Channels
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Choose how security alerts and notifications are delivered to your profile.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-background-secondary/50">
                    <div className="space-y-0.5">
                      <div className="text-xs font-medium text-white flex items-center gap-2">
                        <span>In-App Notification Center</span>
                        <Badge variant="outline" className="text-[10px]">Default</Badge>
                      </div>
                      <p className="text-[11px] text-neutral-400">
                        Receive instant alerts in the top bar bell and notifications dashboard.
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.channels.in_app ?? true}
                      onChange={() => handleToggleChannel("in_app")}
                      className="h-4 w-4 rounded border-border-subtle bg-background-tertiary accent-crimson cursor-pointer"
                    />
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-background-secondary/50">
                    <div className="space-y-0.5">
                      <div className="text-xs font-medium text-white flex items-center gap-2">
                        <span>Email Notifications</span>
                        <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-800">
                          SMTP Required
                        </Badge>
                      </div>
                      <p className="text-[11px] text-neutral-400">
                        Dispatch email digests for critical vulnerabilities and required approvals.
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={preferences.channels.email ?? true}
                      onChange={() => handleToggleChannel("email")}
                      className="h-4 w-4 rounded border-border-subtle bg-background-tertiary accent-crimson cursor-pointer"
                    />
                  </div>

                  <div className="p-3 rounded-lg bg-neutral-900/60 border border-neutral-800 text-[11px] text-neutral-400 flex items-start gap-2">
                    <Info className="h-4 w-4 text-neutral-500 shrink-0 mt-0.5" />
                    <span>
                      External email delivery operates in a safe degraded state if no SMTP server is configured in deployment environment variables.
                    </span>
                  </div>
                </CardContent>
              </Card>

              {/* Severity Threshold */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Shield className="h-4 w-4 text-crimson" />
                    Minimum Severity Threshold
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Suppress notifications below this severity level to minimize alert noise.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {(["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((sev) => {
                      const isSelected = preferences.min_severity === sev;
                      return (
                        <button
                          key={sev}
                          type="button"
                          onClick={() => setPreferences({ ...preferences, min_severity: sev })}
                          className={`p-3 rounded-lg border text-left transition-all ${
                            isSelected
                              ? "bg-crimson/15 border-crimson text-white font-semibold"
                              : "bg-background-secondary/40 border-border-subtle text-neutral-400 hover:border-neutral-600"
                          }`}
                        >
                          <div className="text-xs font-mono uppercase">{sev}</div>
                          <div className="text-[10px] text-neutral-500 mt-1">
                            {sev === "LOW" && "Receive all security notifications"}
                            {sev === "MEDIUM" && "Exclude informational notices"}
                            {sev === "HIGH" && "High and critical issues only"}
                            {sev === "CRITICAL" && "Emergency security alerts only"}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Event Categories */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Bell className="h-4 w-4 text-amber-400" />
                    Security Event Categories
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Select which security event types trigger notifications for your user account.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {Object.entries(categoryLabels).map(([cat, info]) => {
                    const isSubscribed = preferences.categories[cat] ?? true;
                    return (
                      <div
                        key={cat}
                        className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-background-secondary/50"
                      >
                        <div className="space-y-0.5">
                          <span className="text-xs font-medium text-white">{info.label}</span>
                          <p className="text-[11px] text-neutral-400">{info.desc}</p>
                        </div>
                        <input
                          type="checkbox"
                          checked={isSubscribed}
                          onChange={() => handleToggleCategory(cat)}
                          className="h-4 w-4 rounded border-border-subtle bg-background-tertiary accent-crimson cursor-pointer"
                        />
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
