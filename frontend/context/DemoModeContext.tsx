"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface DemoModeContextType {
  isDemoMode: boolean;
  setDemoMode: (enabled: boolean) => void;
  toggleDemoMode: () => void;
}

const DemoModeContext = createContext<DemoModeContextType | undefined>(undefined);

const DEMO_STORAGE_KEY = "shadowops_demo_mode_enabled";

export function DemoModeProvider({ children }: { children: React.ReactNode }) {
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(DEMO_STORAGE_KEY);
      if (stored === "true") {
        setIsDemoMode(true);
      }
    }
  }, []);

  const setDemoMode = (enabled: boolean) => {
    setIsDemoMode(enabled);
    if (typeof window !== "undefined") {
      localStorage.setItem(DEMO_STORAGE_KEY, enabled ? "true" : "false");
    }
  };

  const toggleDemoMode = () => setDemoMode(!isDemoMode);

  return (
    <DemoModeContext.Provider value={{ isDemoMode, setDemoMode, toggleDemoMode }}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode(): DemoModeContextType {
  const context = useContext(DemoModeContext);
  if (!context) {
    throw new Error("useDemoMode must be used within a DemoModeProvider");
  }
  return context;
}
