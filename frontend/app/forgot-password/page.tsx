"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Shield, ArrowLeft, CheckCircle2 } from "lucide-react";

export default function ForgotPasswordPage() {
  const { resetPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSent, setIsSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsLoading(true);
    setError(null);

    try {
      await resetPassword(email);
      setIsSent(true);
    } catch (err: any) {
      console.error("Password reset failure:", err);
      let msg = "Failed to send reset email. Verify email address.";
      if (err.code === "auth/user-not-found") {
        msg = "No account found with this email.";
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
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="h-10 w-10 rounded-lg bg-crimson/20 border border-crimson flex items-center justify-center text-crimson-light">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold tracking-wider text-white">
            SHADOW<span className="text-crimson">OPS</span>
          </h1>
          <p className="text-xs text-neutral-400 font-mono">
            CREDENTIAL RECOVERY
          </p>
        </div>

        <Card variant="bordered">
          <CardHeader>
            <CardTitle className="text-base">Reset Password</CardTitle>
            <CardDescription>
              We will transmit a cryptographic reset link to your authorized email address.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isSent ? (
              <div className="space-y-4 text-center">
                <div className="flex justify-center">
                  <CheckCircle2 className="h-10 w-10 text-emerald-400" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-semibold text-white">Reset Link Dispatched</h4>
                  <p className="text-xs text-neutral-400">
                    If an account exists for <span className="text-white font-mono">{email}</span>, password reset instructions have been sent.
                  </p>
                </div>
                <Link href="/login" className="inline-block w-full">
                  <Button variant="secondary" className="w-full" size="sm">
                    Return to Login
                  </Button>
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && <Alert variant="error">{error}</Alert>}

                <Input
                  label="Registered Email"
                  type="email"
                  placeholder="analyst@organization.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />

                <Button
                  type="submit"
                  variant="primary"
                  className="w-full"
                  isLoading={isLoading}
                >
                  Dispatch Reset Instructions
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        <div className="text-center">
          <Link
            href="/login"
            className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Authentication
          </Link>
        </div>
      </div>
    </div>
  );
}
