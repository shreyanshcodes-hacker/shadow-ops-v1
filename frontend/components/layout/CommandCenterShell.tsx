"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shield,
  Radio,
  Server,
  Terminal,
  Users,
  Bell,
  LogOut,
  AlertOctagon,
  FileText,
  MessageSquare,
  Wrench,
  Sliders,
  CheckCircle2,
} from "lucide-react";
import { WorkspaceSwitcher } from "@/components/workspace/WorkspaceSwitcher";
import { useAuth } from "@/context/AuthContext";

interface NavItem {
  name: string;
  href: string;
  icon: any;
  implemented: boolean;
  badge?: string;
}

export function CommandCenterShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { profile, logout } = useAuth();

  const navItems: NavItem[] = [
    { name: "Command Center", href: "/dashboard", icon: Radio, implemented: true },
    { name: "Assets & Boundary", href: "/assets", icon: Server, implemented: true },
    { name: "Scans & Runs", href: "/scans", icon: Terminal, implemented: true },
    { name: "Attack Paths", href: "/attack-paths", icon: Sliders, implemented: true },
    { name: "AI Security Team", href: "/security-team", icon: Users, implemented: true },
    { name: "Remediation", href: "/remediations", icon: Wrench, implemented: true },
    { name: "Verification", href: "/verifications", icon: CheckCircle2, implemented: true },
    { name: "Notifications", href: "/notifications", icon: Bell, implemented: true },
    { name: "Workflows", href: "/workflows", icon: Sliders, implemented: true },
    { name: "Reports", href: "/reports", icon: FileText, implemented: true },
    { name: "Team & Access", href: "/team", icon: Users, implemented: true },
    { name: "AI Security Chat", href: "/chat", icon: MessageSquare, implemented: true },
  ];

  return (
    <div className="flex h-screen bg-background text-neutral-200 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border-subtle bg-background-secondary flex flex-col shrink-0">
        {/* Brand */}
        <div className="h-14 border-b border-border-subtle px-4 flex items-center">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded bg-crimson/20 border border-crimson flex items-center justify-center text-crimson-light">
              <Shield className="h-4 w-4" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold tracking-wider text-sm text-white">
                SHADOW<span className="text-crimson">OPS</span>
              </span>
              <span className="text-[9px] text-neutral-400 font-mono tracking-tighter">
                AI DEFENSE PLATFORM
              </span>
            </div>
          </Link>
        </div>

        {/* Workspace Switcher */}
        <div className="p-3 border-b border-border-subtle">
          <WorkspaceSwitcher />
        </div>

        {/* Nav Links */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            if (!item.implemented) {
              return (
                <div
                  key={item.name}
                  className="flex items-center justify-between px-3 py-2 rounded-md text-neutral-500 text-xs font-medium cursor-not-allowed select-none opacity-60"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span className="text-[9px] font-mono px-1.5 py-0.2 bg-neutral-900 border border-neutral-800 text-neutral-500 rounded">
                      {item.badge}
                    </span>
                  )}
                </div>
              );
            }

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors ${
                  isActive
                    ? "bg-crimson/10 text-white border border-crimson/30 shadow-crimson-glow"
                    : "text-neutral-400 hover:bg-background-tertiary hover:text-white"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`h-4 w-4 ${isActive ? "text-crimson" : ""}`} />
                  <span>{item.name}</span>
                </div>
              </Link>
            );
          })}
        </nav>

        {/* User Profile Card & Sign Out */}
        <div className="p-3 border-t border-border-subtle bg-background-tertiary/40 flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="h-7 w-7 rounded-full bg-crimson/20 border border-crimson/60 flex items-center justify-center text-xs font-bold text-white shrink-0">
              {profile?.display_name ? profile.display_name.slice(0, 2).toUpperCase() : "OP"}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-medium text-white truncate">
                {profile?.display_name || "Security Operator"}
              </span>
              <span className="text-[10px] text-neutral-400 truncate font-mono">
                {profile?.email || "user@shadowops"}
              </span>
            </div>
          </div>
          <button
            onClick={logout}
            title="Sign Out"
            className="p-1.5 rounded hover:bg-background-elevated text-neutral-400 hover:text-white transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <header className="h-14 border-b border-border-subtle bg-background-secondary/80 backdrop-blur px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-neutral-400 uppercase tracking-wider">
              COMMAND CENTER // {pathname ? pathname.replace("/", "").toUpperCase() : "OVERVIEW"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="px-2.5 py-1 rounded bg-background border border-border-subtle text-xs font-mono text-neutral-300 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span>LIVE SYSTEM</span>
            </div>
            <Link
              href="/notifications"
              className="relative h-8 w-8 rounded-md hover:bg-background-tertiary border border-border-subtle flex items-center justify-center text-neutral-300 hover:text-white transition-colors"
              title="Notifications"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-crimson" />
            </Link>
          </div>
        </header>

        {/* Workspace Body */}
        <main className="flex-1 overflow-y-auto p-6 bg-background">
          {children}
        </main>
      </div>
    </div>
  );
}
