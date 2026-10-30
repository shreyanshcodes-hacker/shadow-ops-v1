"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useWorkspace } from "@/context/WorkspaceContext";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export function ProtectedRoute({
  children,
  requireVerifiedEmail = false,
}: {
  children: React.ReactNode;
  requireVerifiedEmail?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { profile, loading, isAuthenticated, isEmailVerified } = useAuth();
  const { workspaces, loadingWorkspaces } = useWorkspace();

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        router.push("/login");
      } else if (requireVerifiedEmail && !isEmailVerified) {
        router.push("/verify-email");
      } else if (!loadingWorkspaces) {
        // If user is authenticated but not affiliated with any workspace/company,
        // redirect to the onboarding flow (unless already on onboarding).
        if (workspaces.length === 0 && pathname !== "/onboarding") {
          router.push("/onboarding");
        }
      }
    }
  }, [loading, isAuthenticated, isEmailVerified, requireVerifiedEmail, loadingWorkspaces, workspaces.length, pathname, router]);

  if (loading || (!loading && isAuthenticated && loadingWorkspaces)) {
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

  if (workspaces.length === 0 && pathname !== "/onboarding") {
    return null;
  }

  return <>{children}</>;
}
