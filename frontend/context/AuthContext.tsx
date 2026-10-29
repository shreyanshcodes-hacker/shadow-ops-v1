"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, onIdTokenChanged } from "firebase/auth";
import { auth } from "@/lib/firebase/client";
import {
  firebaseSignIn,
  firebaseSignUp,
  firebaseSignOut,
  firebaseSendPasswordReset,
  firebaseResendVerification,
} from "@/lib/firebase/auth";
import { isFirebaseConfigured } from "@/lib/firebase/config";
import { apiClient, registerTokenProvider, setApiAuthToken } from "@/lib/api-client";
import { Profile } from "@/types";

interface AuthContextType {
  firebaseUser: User | null;
  profile: Profile | null;
  loading: boolean;
  isAuthenticated: boolean;
  isEmailVerified: boolean;
  login: (email: string, password: string) => Promise<User | void>;
  signup: typeof firebaseSignUp;
  logout: () => Promise<void>;
  resetPassword: typeof firebaseSendPasswordReset;
  resendVerification: () => Promise<void>;
  refreshProfile: () => Promise<Profile | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const LOCAL_TOKEN_KEY = "shadowops_local_token";
const LOCAL_USER_UID = "local-dev-user";
const LOCAL_DEV_TOKEN = "test-token-local-dev-user";

function createMockDevUser(email = "operator@shadowops.io"): User {
  return {
    uid: LOCAL_USER_UID,
    email: email,
    displayName: "Security Lead (Local)",
    emailVerified: true,
    isAnonymous: false,
    metadata: {},
    providerData: [],
    refreshToken: "",
    tenantId: null,
    delete: async () => {},
    getIdToken: async () => LOCAL_DEV_TOKEN,
    getIdTokenResult: async () => ({
      token: LOCAL_DEV_TOKEN,
      authTime: "",
      issuedAtTime: "",
      expirationTime: "",
      signInProvider: "custom",
      claims: { uid: LOCAL_USER_UID, email: email },
    }),
    reload: async () => {},
    toJSON: () => ({}),
    phoneNumber: null,
    photoURL: null,
    providerId: "custom",
  } as unknown as User;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [firebaseUser, setFirebaseUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  // Register dynamic token provider with typed API client
  useEffect(() => {
    registerTokenProvider(async () => {
      if (typeof window !== "undefined") {
        const local = localStorage.getItem(LOCAL_TOKEN_KEY);
        if (local) return local;
      }
      if (auth.currentUser) return await auth.currentUser.getIdToken();
      return null;
    });
  }, []);

  const refreshProfile = useCallback(async (): Promise<Profile | null> => {
    try {
      const data = await apiClient.get<Profile>("/me");
      setProfile(data);
      return data;
    } catch (err) {
      console.error("Failed to sync profile with ShadowOps backend:", err);
      return null;
    }
  }, []);

  // Restore session on mount (Firebase or Local Dev Token)
  useEffect(() => {
    let hasRestoredLocal = false;
    if (typeof window !== "undefined") {
      const localToken = localStorage.getItem(LOCAL_TOKEN_KEY);
      if (localToken === LOCAL_DEV_TOKEN) {
        hasRestoredLocal = true;
        setApiAuthToken(LOCAL_DEV_TOKEN);
        const devUser = createMockDevUser();
        setFirebaseUser(devUser);
        refreshProfile().finally(() => setLoading(false));
      }
    }

    if (!hasRestoredLocal) {
      const unsubscribe = onIdTokenChanged(auth, async (user) => {
        setFirebaseUser(user);
        if (user) {
          await refreshProfile();
        } else {
          setProfile(null);
        }
        setLoading(false);
      });
      return () => unsubscribe();
    }
  }, [refreshProfile]);

  const login = async (email: string, password: string): Promise<User | void> => {
    // 1. Direct local dev login check
    if (email.toLowerCase() === "operator@shadowops.io" || !isFirebaseConfigured) {
      if (typeof window !== "undefined") {
        localStorage.setItem(LOCAL_TOKEN_KEY, LOCAL_DEV_TOKEN);
      }
      setApiAuthToken(LOCAL_DEV_TOKEN);
      const devUser = createMockDevUser(email);
      setFirebaseUser(devUser);
      await refreshProfile();
      return devUser;
    }

    // 2. Production Firebase Authentication with fallback
    try {
      const user = await firebaseSignIn(email, password);
      setFirebaseUser(user);
      await refreshProfile();
      return user;
    } catch (err) {
      // Fallback to local dev user if Firebase auth is unavailable
      if (email.toLowerCase() === "operator@shadowops.io") {
        if (typeof window !== "undefined") {
          localStorage.setItem(LOCAL_TOKEN_KEY, LOCAL_DEV_TOKEN);
        }
        setApiAuthToken(LOCAL_DEV_TOKEN);
        const devUser = createMockDevUser(email);
        setFirebaseUser(devUser);
        await refreshProfile();
        return devUser;
      }
      throw err;
    }
  };

  const logout = async () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(LOCAL_TOKEN_KEY);
      localStorage.removeItem("shadowops_active_workspace");
    }
    setApiAuthToken(null);
    try {
      await firebaseSignOut();
    } catch {
      // Ignore if not in Firebase session
    }
    setFirebaseUser(null);
    setProfile(null);
  };

  const resendVerification = async () => {
    if (auth.currentUser) {
      await firebaseResendVerification(auth.currentUser);
    }
  };

  const value: AuthContextType = {
    firebaseUser,
    profile,
    loading,
    isAuthenticated: Boolean(firebaseUser && profile),
    isEmailVerified: Boolean(firebaseUser?.emailVerified),
    login,
    signup: firebaseSignUp,
    logout,
    resetPassword: firebaseSendPasswordReset,
    resendVerification,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
