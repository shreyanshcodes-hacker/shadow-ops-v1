"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Shield } from "lucide-react";

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !email || !password) return;

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await signup(email, password, name);
      router.push("/verify-email");
    } catch (err: any) {
      console.error("Signup failure:", err);
      let msg = "Failed to create account. Please check your information.";
      if (err.code === "auth/email-already-in-use") {
        msg = "An account with this email address already exists.";
      } else if (err.code === "auth/weak-password") {
        msg = "Password is too weak. Must include letters and numbers.";
      } else if (err.code === "auth/invalid-email") {
        msg = "Invalid email format.";
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
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
            BUILD YOUR AI SECURITY TEAM
          </p>
        </div>

        {/* Local Demo Account Banner */}
        <div className="p-3.5 rounded-xl bg-neutral-900/80 border border-emerald-500/30 text-xs text-neutral-300 space-y-2">
          <div className="font-semibold text-emerald-400 font-mono text-[11px] uppercase tracking-wider">
            Local Development Mode Active
          </div>
          <p className="text-[11px] text-neutral-400">
            A pre-configured security operator account is already seeded in your local database.
          </p>
          <Link href="/login" className="block">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full border-emerald-500/40 text-emerald-400 hover:bg-emerald-950/40 font-mono text-xs"
            >
              Go to Sign In (operator@shadowops.io)
            </Button>
          </Link>
        </div>

        <Card variant="bordered">
          <CardHeader>
            <CardTitle className="text-base">Create Security Account</CardTitle>
            <CardDescription>
              Provision your autonomous multi-tenant cybersecurity command center.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && <Alert variant="error">{error}</Alert>}

              <Input
                label="Full Name"
                type="text"
                placeholder="Jane Doe"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoComplete="name"
              />

              <Input
                label="Work Email"
                type="email"
                placeholder="analyst@organization.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />

              <Input
                label="Security Password"
                type="password"
                placeholder="Minimum 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />

              <Input
                label="Confirm Password"
                type="password"
                placeholder="Repeat password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
              />

              <Button
                type="submit"
                variant="primary"
                className="w-full"
                isLoading={isLoading}
              >
                Provision Account
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="text-center text-xs text-neutral-400">
          Already registered?{" "}
          <Link href="/login" className="text-crimson font-medium hover:underline">
            Access operations center
          </Link>
        </div>
      </div>
    </div>
  );
}
