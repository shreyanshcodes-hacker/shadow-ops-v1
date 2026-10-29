"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Shield, User, Code2, Sparkles, Terminal, ArrowLeft } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background text-neutral-100 flex flex-col justify-between">
      {/* Top Navbar */}
      <header className="h-16 border-b border-border-subtle bg-background-secondary/80 backdrop-blur px-8 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded bg-crimson/20 border border-crimson flex items-center justify-center text-crimson-light">
            <Shield className="h-5 w-5" />
          </div>
          <span className="font-bold tracking-wider text-base text-white">
            SHADOW<span className="text-crimson">OPS</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <Link href="/">
            <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-neutral-300 hover:text-white">
              <ArrowLeft className="h-3.5 w-3.5" />
              Home
            </Button>
          </Link>
          <Link href="/login">
            <Button variant="secondary" size="sm" className="text-xs">
              Sign In
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl mx-auto px-6 py-12 w-full">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Header section */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border-subtle">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded bg-crimson/20 border border-crimson flex items-center justify-center text-crimson-light">
                  <Shield className="h-4 w-4" />
                </div>
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  About ShadowOps
                </h1>
              </div>
              <p className="text-xs font-mono text-neutral-400">
                PLATFORM OVERVIEW & DEVELOPER INFORMATION
              </p>
            </div>

            {/* Branding Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-crimson/10 border border-crimson/40 text-xs font-mono text-crimson-light">
                <Sparkles className="h-3.5 w-3.5" />
                Built with ShreyanshCodes
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-background-elevated border border-border-subtle text-xs font-mono text-neutral-300">
                <Code2 className="h-3.5 w-3.5 text-crimson" />
                Powered by ShreyanshCodes
              </span>
            </div>
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Card 1: About ShadowOps */}
            <Card className="md:col-span-2 bg-background-secondary border border-border-subtle">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Terminal className="h-5 w-5 text-crimson" />
                  <CardTitle className="text-base font-semibold text-white">
                    About ShadowOps
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-neutral-300 leading-relaxed">
                  ShadowOps is an AI-powered cybersecurity platform designed to help teams identify vulnerabilities, understand security risks, explore attack paths, and manage remediation workflows.
                </p>
              </CardContent>
            </Card>

            {/* Card 2: About the Developer */}
            <Card className="bg-background-secondary border border-border-subtle">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-crimson" />
                  <CardTitle className="text-base font-semibold text-white">
                    About the Developer
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="relative h-20 w-20 rounded-xl overflow-hidden border-2 border-crimson/50 shadow-md shrink-0 bg-neutral-900">
                    <Image
                      src="/founder.jpg"
                      alt="Shreyansh Jaiswal"
                      width={80}
                      height={80}
                      className="w-full h-full object-cover"
                      priority
                    />
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-white tracking-wide">
                      Shreyansh Jaiswal
                    </h4>
                    <p className="text-xs font-mono text-crimson-light mt-0.5">
                      CREATOR & LEAD DEVELOPER
                    </p>
                  </div>
                </div>
                <p className="text-sm text-neutral-300 leading-relaxed">
                  Developer of ShadowOps and creator of ShreyanshCodes, focused on building practical software products using AI, automation, and modern web technologies.
                </p>
              </CardContent>
            </Card>

            {/* Card 3: Built with ShreyanshCodes */}
            <Card className="bg-background-secondary border border-border-subtle">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Code2 className="h-5 w-5 text-crimson" />
                  <CardTitle className="text-base font-semibold text-white">
                    Built with ShreyanshCodes
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-neutral-300 leading-relaxed">
                  ShadowOps is built by Shreyansh Jaiswal under the ShreyanshCodes development brand.
                </p>
                <div className="pt-2 flex flex-col sm:flex-row gap-2">
                  <div className="p-2.5 rounded bg-background border border-border-subtle flex items-center gap-2 text-xs font-mono text-neutral-300">
                    <span className="h-2 w-2 rounded-full bg-crimson" />
                    <span>Built with ShreyanshCodes</span>
                  </div>
                  <div className="p-2.5 rounded bg-background border border-border-subtle flex items-center gap-2 text-xs font-mono text-neutral-300">
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                    <span>Powered by ShreyanshCodes</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Footer Branding Bar */}
          <div className="p-4 rounded-lg bg-background-tertiary/40 border border-border-subtle flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-mono text-neutral-400">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-crimson animate-pulse" />
              <span>SHADOWOPS PLATFORM // VERSION 2.0</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-crimson-light font-semibold">Built with ShreyanshCodes</span>
              <span>•</span>
              <span className="text-neutral-300">Powered by ShreyanshCodes</span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="h-14 border-t border-border-subtle bg-background-secondary/50 px-8 flex items-center justify-between text-xs text-neutral-500 font-mono">
        <span>SHADOWOPS PLATFORM // VERSION 2.0</span>
        <span>SECURITY BOUNDARIES ACTIVE</span>
      </footer>
    </div>
  );
}
