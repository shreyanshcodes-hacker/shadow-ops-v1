"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export function ProtectedRoute({
  children,
  requireVerifiedEmail = false,
}: {
  children: React.ReactNode;
  requireVerifiedEmail?: boolean;
}) {
  const router = useRouter();
  const { firebaseUser, profile, loading, isAuthenticated, isEmailVerified } = useAuth();

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (requireVerifiedEmail && !isEmailVerified) {
        router.push("/verify-email");
      }
    }
  }, [loading, isAuthenticated, isEmailVerified, requireVerifiedEmail, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center space-y-3">
        <LoadingSpinner size="lg" />
        <span className="text-xs font-mono text-neutral-400">
          RESTORING SECURITY SESSION...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  if (requireVerifiedEmail && !isEmailVerified) {
    return null;
  }

  return <>{children}</>;
}
