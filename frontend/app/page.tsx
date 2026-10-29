import Link from "next/link";
import { Shield, Lock, Terminal, Activity, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-neutral-100 flex flex-col justify-between">
      {/* Top Navbar */}
      <header className="h-16 border-b border-border-subtle bg-background-secondary/80 backdrop-blur px-8 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded bg-crimson/20 border border-crimson flex items-center justify-center text-crimson-light">
            <Shield className="h-5 w-5" />
          </div>
          <span className="font-bold tracking-wider text-base text-white">
            SHADOW<span className="text-crimson">OPS</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link href="/about">
            <Button variant="ghost" size="sm" className="text-neutral-300 hover:text-white">
              About Us
            </Button>
          </Link>
          <Link href="/login">
            <Button variant="ghost" size="sm">
              Sign In
            </Button>
          </Link>
          <Link href="/signup">
            <Button variant="primary" size="sm">
              Deploy AI Team
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-20 flex flex-col items-center text-center space-y-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-crimson/10 border border-crimson/30 text-xs font-mono text-crimson-light">
          <span className="h-1.5 w-1.5 rounded-full bg-crimson animate-pulse" />
          <span>AUTONOMOUS CYBERSECURITY TEAM FOR STARTUPS</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white max-w-3xl leading-tight">
          Your AI Security Team. <br />
          <span className="text-crimson">Always Watching.</span>
        </h1>

        <p className="text-base text-neutral-400 max-w-2xl leading-relaxed">
          ShadowOps continuously discovers vulnerabilities, analyzes attack paths, enforces zero-trust authorization boundaries, and coordinates autonomous AI agents across your repositories and cloud infrastructure.
        </p>

        <div className="flex flex-wrap gap-4 justify-center pt-4">
          <Link href="/signup">
            <Button variant="primary" size="lg" className="gap-2">
              <span>Start Security Operations</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary" size="lg">
              Access Existing Command Center
            </Button>
          </Link>
        </div>

        {/* Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-16 text-left w-full">
          <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle">
            <Lock className="h-6 w-6 text-crimson mb-3" />
            <h3 className="text-sm font-semibold text-white mb-1">
              Zero-Trust Scanning Gateway
            </h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Enforces <code className="text-crimson font-mono">NO AUTHORIZATION → NO SCAN</code>. Scans only execute against cryptographically verified assets.
            </p>
          </div>

          <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle">
            <Terminal className="h-6 w-6 text-crimson mb-3" />
            <h3 className="text-sm font-semibold text-white mb-1">
              Multi-Tenant Workspaces
            </h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Strict isolation per workspace, hardened RBAC roles, and complete immutable audit logging across all team members.
            </p>
          </div>

          <div className="p-6 rounded-lg bg-background-secondary border border-border-subtle">
            <Activity className="h-6 w-6 text-crimson mb-3" />
            <h3 className="text-sm font-semibold text-white mb-1">
              AI-Native Defense Agents
            </h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              Gemini and Grok agent architectures built for static analysis, dependency graph auditing, and verifiable remediation.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-14 border-t border-border-subtle bg-background-secondary/50 px-8 flex items-center justify-between text-xs text-neutral-500 font-mono">
        <span>SHADOWOPS PLATFORM // VERSION 2.0</span>
        <div className="flex items-center gap-6">
          <Link href="/about" className="hover:text-neutral-300 transition-colors">
            About Us
          </Link>
          <span>SECURITY BOUNDARIES ACTIVE</span>
        </div>
      </footer>
    </div>
  );
}
