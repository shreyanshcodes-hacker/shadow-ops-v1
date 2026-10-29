"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Shield, KeyRound, Sparkles } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("operator@shadowops.io");
  const [password, setPassword] = useState("Password123!");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsLoading(true);
    setError(null);

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      console.error("Login failure:", err);
      let msg = "Invalid credentials. Please verify your email and password.";
      if (
        err.code === "auth/user-not-found" ||
        err.code === "auth/wrong-password" ||
        err.code === "auth/invalid-credential"
      ) {
        msg = "Invalid email or password.";
      } else if (err.code === "auth/too-many-requests") {
        msg = "Too many failed attempts. Please try again later or reset password.";
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoLogin = async () => {
    setEmail("operator@shadowops.io");
    setPassword("Password123!");
    setIsLoading(true);
    setError(null);
    try {
      await login("operator@shadowops.io", "Password123!");
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.message || "Quick demo login failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="h-10 w-10 rounded-lg bg-crimson/20 border border-crimson flex items-center justify-center text-crimson-light">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold tracking-wider text-white">
            SHADOW<span className="text-crimson">OPS</span>
          </h1>
          <p className="text-xs text-neutral-400 font-mono">
            ACCESS YOUR SECURITY OPERATIONS CENTER
          </p>
        </div>

        {/* Local Demo Credentials Card */}
        <div className="p-3.5 rounded-xl bg-neutral-900/80 border border-emerald-500/30 text-xs text-neutral-300 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-emerald-400 flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider">
              <KeyRound className="h-3.5 w-3.5" />
              Local Development Account
            </span>
            <span className="text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-600/40 px-1.5 py-0.5 rounded font-mono">
              PRE-CONFIGURED
            </span>
          </div>
          <div className="text-[11px] font-mono text-neutral-400 space-y-0.5 bg-neutral-950 p-2 rounded border border-neutral-800">
            <div>Email: <strong className="text-neutral-200">operator@shadowops.io</strong></div>
            <div>Password: <strong className="text-neutral-200">Password123!</strong></div>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleQuickDemoLogin}
            disabled={isLoading}
            className="w-full gap-2 border-emerald-500/40 text-emerald-400 hover:bg-emerald-950/40 font-mono text-xs"
          >
            <Sparkles className="h-3.5 w-3.5" />
            1-Click Login as Security Lead
          </Button>
        </div>

        <Card variant="bordered">
          <CardHeader>
            <CardTitle className="text-base">Sign In</CardTitle>
            <CardDescription>
              Enter your credentials to access your autonomous security perimeter.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && <Alert variant="error">{error}</Alert>}

              <Input
                label="Corporate Email"
                type="email"
                placeholder="analyst@organization.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />

              <div className="space-y-1">
                <Input
                  label="Password"
                  type="password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
                <div className="flex justify-end pt-1">
                  <Link
                    href="/forgot-password"
                    className="text-xs text-neutral-400 hover:text-crimson transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                className="w-full"
                isLoading={isLoading}
              >
                Authenticate Session
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="text-center text-xs text-neutral-400">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-crimson font-medium hover:underline">
            Build your AI security team
          </Link>
        </div>
      </div>
    </div>
  );
}
