"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Shield, MailCheck, RotateCw, LogOut } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { Workspace } from "@/types";

export default function VerifyEmailPage() {
  const router = useRouter();
  const { firebaseUser, resendVerification, logout, refreshProfile } = useAuth();
  const [isResending, setIsResending] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleResend = async () => {
    setIsResending(true);
    setMessage(null);
    setError(null);
    try {
      await resendVerification();
      setMessage("Verification email has been re-sent. Please check your inbox and spam folder.");
    } catch (err: any) {
      setError(err?.message || "Failed to resend verification link.");
    } finally {
      setIsResending(false);
    }
  };

  const handleRefresh = async () => {
    setIsChecking(true);
    setMessage(null);
    setError(null);
    try {
      if (firebaseUser) {
        await firebaseUser.reload();
        if (firebaseUser.emailVerified) {
          await refreshProfile();
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
          return;
        }
      }
      setMessage("Email is not verified yet. Please click the confirmation link in your inbox.");
    } catch (err: any) {
      setError(err?.message || "Failed to refresh verification status.");
    } finally {
      setIsChecking(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push("/login");
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
            IDENTITY VERIFICATION GATEWAY
          </p>
        </div>

        <Card variant="bordered">
          <CardHeader>
            <div className="flex justify-center mb-2">
              <MailCheck className="h-10 w-10 text-crimson" />
            </div>
            <CardTitle className="text-base text-center">Verify Your Work Email</CardTitle>
            <CardDescription className="text-center">
              A verification dispatch was transmitted to:{" "}
              <span className="text-white font-mono block mt-1">
                {firebaseUser?.email || "your email address"}
              </span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {message && <Alert variant="info">{message}</Alert>}
            {error && <Alert variant="error">{error}</Alert>}

            <p className="text-xs text-neutral-400 leading-relaxed text-center">
              ShadowOps strictly requires confirmed email verification before workspace authorization and security scanning can be unlocked.
            </p>

            <div className="flex flex-col gap-2 pt-2">
              <Button
                variant="primary"
                className="w-full"
                onClick={handleRefresh}
                isLoading={isChecking}
              >
                <RotateCw className="h-4 w-4" />
                I Have Verified My Email
              </Button>

              <Button
                variant="secondary"
                className="w-full"
                onClick={handleResend}
                isLoading={isResending}
              >
                Resend Verification Link
              </Button>

              <Button
                variant="ghost"
                className="w-full text-neutral-400 hover:text-white"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
