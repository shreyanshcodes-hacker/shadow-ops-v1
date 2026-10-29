import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { WorkspaceProvider } from "@/context/WorkspaceContext";
import { DemoModeProvider } from "@/context/DemoModeContext";

export const metadata: Metadata = {
  title: "ShadowOps | AI Security Team",
  description: "AI-native security command center for startups and engineering teams. Always watching.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-neutral-100 flex flex-col">
        <AuthProvider>
          <WorkspaceProvider>
            <DemoModeProvider>{children}</DemoModeProvider>
          </WorkspaceProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
