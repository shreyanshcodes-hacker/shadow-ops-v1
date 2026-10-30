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
import { apiClient } from "@/lib/api-client";
import { Workspace } from "@/types";

export default function SignupPage() {
  const router = useRouter();
  const { signup, loginWithGoogle } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigateAfterAuth = async () => {
    try {
      const list = await apiClient.get<Workspace[]>("/workspaces");
      if (list && list.length > 0) {
        router.push("/dashboard");
      } else {
        router.push("/onboarding");
      }
    } catch {
      router.push("/onboarding");
    }
  };

  const handleGoogleSignup = async () => {
    setIsGoogleLoading(true);
    setError(null);
    try {
      await loginWithGoogle();
      await navigateAfterAuth();
    } catch (err: any) {
      console.error("Google sign-up failure:", err);
      let msg = "Google authentication failed. Please try again.";
      if (err.code === "auth/popup-closed-by-user") {
        msg = "Sign-up popup was closed before completing.";
      } else if (err.code === "auth/cancelled-popup-request") {
        msg = "Popup request cancelled.";
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
    } finally {
      setIsGoogleLoading(false);
    }
  };

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

        <Card variant="bordered">
          <CardHeader>
            <CardTitle className="text-base">Create Security Account</CardTitle>
            <CardDescription>
              Provision your autonomous multi-tenant cybersecurity command center.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {error && <Alert variant="error">{error}</Alert>}

            {/* Google Sign-in Option */}
            <Button
              type="button"
              variant="outline"
              onClick={handleGoogleSignup}
              disabled={isLoading || isGoogleLoading}
              className="w-full flex items-center justify-center gap-2.5 bg-background border border-border-subtle hover:bg-neutral-800 text-neutral-200 transition-colors font-medium text-xs h-10"
            >
              <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>{isGoogleLoading ? "Connecting with Google..." : "Continue with Google"}</span>
            </Button>

            <div className="relative flex items-center justify-center my-3">
              <div className="border-t border-border-subtle w-full" />
              <span className="bg-background-secondary px-2 text-[10px] font-mono uppercase text-neutral-400 absolute">
                Or continue with email
              </span>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">

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
