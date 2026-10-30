"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useWorkspace } from "@/context/WorkspaceContext";
import { apiClient } from "@/lib/api-client";
import {
  WorkspaceDirectoryItem,
  CompanyOnboardingRequest,
  EmployeeJoinRequest,
  Workspace,
  AssetType,
  AssetCriticality,
} from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import {
  Shield,
  Building2,
  Users,
  Search,
  ArrowRight,
  CheckCircle2,
  Server,
  Layers,
  ArrowLeft,
  LogOut,
  Sparkles,
  UserCheck,
} from "lucide-react";

type OnboardingBranch = "select" | "company" | "employee";

export default function OnboardingPage() {
  const router = useRouter();
  const { profile, firebaseUser, logout, refreshProfile } = useAuth();
  const { workspaces, refreshWorkspaces, setActiveWorkspace, loadingWorkspaces } = useWorkspace();

  const [activeBranch, setActiveBranch] = useState<OnboardingBranch>("select");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If user already has active workspaces, redirect them to dashboard
  useEffect(() => {
    if (!loadingWorkspaces && workspaces.length > 0) {
      router.replace("/dashboard");
    }
  }, [loadingWorkspaces, workspaces.length, router]);

  // --- Branch 1: Company Onboarding State ---
  const [companyName, setCompanyName] = useState("");
  const [slug, setSlug] = useState("");
  const [industry, setIndustry] = useState("Fintech & Banking");
  const [teamSize, setTeamSize] = useState("11-50");
  const [ownerDisplayName, setOwnerDisplayName] = useState(
    profile?.display_name || firebaseUser?.displayName || ""
  );
  // Initial Asset State
  const [assetName, setAssetName] = useState("");
  const [assetType, setAssetType] = useState<AssetType>("repository");
  const [assetIdentifier, setAssetIdentifier] = useState("");
  const [assetEnvironment, setAssetEnvironment] = useState("production");
  const [assetCriticality, setAssetCriticality] = useState<AssetCriticality>("high");

  // Keep slug synchronized with company name until manually customized
  const handleCompanyNameChange = (val: string) => {
    setCompanyName(val);
    const autoSlug = val
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    setSlug(autoSlug);
  };

  // --- Branch 2: Employee Onboarding State ---
  const [employeeName, setEmployeeName] = useState(
    profile?.display_name || firebaseUser?.displayName || ""
  );
  const [jobTitle, setJobTitle] = useState("");
  const [directorySearch, setDirectorySearch] = useState("");
  const [companies, setCompanies] = useState<WorkspaceDirectoryItem[]>([]);
  const [searchingDirectory, setSearchingDirectory] = useState(false);
  const [joiningCompanyId, setJoiningCompanyId] = useState<string | null>(null);

  // Query directory with debounced search
  const fetchDirectory = useCallback(async (query: string) => {
    setSearchingDirectory(true);
    try {
      const endpoint = query ? `/workspaces/directory?q=${encodeURIComponent(query)}` : "/workspaces/directory";
      const results = await apiClient.get<WorkspaceDirectoryItem[]>(endpoint);
      setCompanies(results);
    } catch (err: any) {
      console.error("Failed to fetch company directory:", err);
    } finally {
      setSearchingDirectory(false);
    }
  }, []);

  useEffect(() => {
    if (activeBranch === "employee") {
      const timer = setTimeout(() => {
        fetchDirectory(directorySearch);
      }, 250);
      return () => clearTimeout(timer);
    }
  }, [activeBranch, directorySearch, fetchDirectory]);

  // Handle Branch 1 Submission (Register as Company)
  const handleCompanySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim()) {
      setError("Please specify a company name.");
      return;
    }

    setSubmitting(true);
    setError(null);

    const payload: CompanyOnboardingRequest = {
      company_name: companyName.trim(),
      slug: slug.trim() || undefined,
      industry: industry || undefined,
      team_size: teamSize || undefined,
      display_name: ownerDisplayName.trim() || undefined,
      asset_name: assetName.trim() || undefined,
      asset_type: assetType,
      asset_identifier: assetIdentifier.trim() || undefined,
      asset_environment: assetEnvironment,
      asset_criticality: assetCriticality,
    };

    try {
      const createdWorkspace = await apiClient.post<Workspace>("/workspaces/onboarding/company", payload);
      setSuccessMessage(`Company workspace "${createdWorkspace.name}" successfully created with primary asset!`);
      await refreshProfile();
      await refreshWorkspaces();
      setActiveWorkspace(createdWorkspace);
      router.push("/dashboard");
    } catch (err: any) {
      console.error("Company onboarding failed:", err);
      setError(err?.response?.data?.error?.message || err?.message || "Failed to complete company setup.");
      setSubmitting(false);
    }
  };

  // Handle Branch 2 Submission (Join Company as Employee)
  const handleJoinCompany = async (targetCompany: WorkspaceDirectoryItem) => {
    if (!employeeName.trim()) {
      setError("Please enter your full name before joining a company.");
      return;
    }

    setJoiningCompanyId(targetCompany.id);
    setError(null);

    const payload: EmployeeJoinRequest = {
      display_name: employeeName.trim(),
      job_title: jobTitle.trim() || undefined,
    };

    try {
      const joinedWs = await apiClient.post<Workspace>(`/workspaces/${targetCompany.id}/join`, payload);
      setSuccessMessage(`Successfully joined ${targetCompany.name}! Redirecting to command center...`);
      await refreshProfile();
      await refreshWorkspaces();
      setActiveWorkspace(joinedWs);
      router.push("/dashboard");
    } catch (err: any) {
      console.error("Employee join failed:", err);
      setError(err?.response?.data?.error?.message || err?.message || "Failed to join company workspace.");
      setJoiningCompanyId(null);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-background text-neutral-100 flex flex-col justify-between">
      {/* Top Navigation Bar */}
      <header className="border-b border-border-subtle bg-surface/60 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-crimson/20 border border-crimson flex items-center justify-center text-crimson-light">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-wider text-white">
              SHADOW<span className="text-crimson">OPS</span>
            </div>
            <div className="text-[10px] text-neutral-400 font-mono tracking-tight">
              AUTONOMOUS SECURITY COMMAND
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="text-xs text-neutral-400 font-mono hidden sm:block">
            Signed in as:{" "}
            <span className="text-neutral-200">
              {profile?.email || firebaseUser?.email || "Authenticated Operator"}
            </span>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-xs">
            <LogOut className="h-3.5 w-3.5 mr-1.5" />
            Sign Out
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-8 flex flex-col justify-center">
        {error && (
          <Alert variant="error" className="mb-6">
            {error}
          </Alert>
        )}

        {successMessage && (
          <Alert variant="success" className="mb-6">
            {successMessage}
          </Alert>
        )}

        {/* STEP 1: Branch Selection */}
        {activeBranch === "select" && (
          <div className="space-y-8 animate-fadeIn">
            <div className="text-center space-y-2">
              <Badge variant="outline" className="border-crimson/40 text-crimson font-mono text-[11px] mb-1">
                SYSTEM ONBOARDING PROCESS
              </Badge>
              <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white">
                How would you like to use ShadowOps?
              </h1>
              <p className="text-sm text-neutral-400 max-w-lg mx-auto">
                Set up an organization command center to protect your company&apos;s digital assets, or join an existing security workspace.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
              {/* Option 1: Register as a Company */}
              <div
                onClick={() => {
                  setError(null);
                  setActiveBranch("company");
                }}
                className="group relative cursor-pointer rounded-xl border border-border-subtle bg-surface/50 p-6 transition-all duration-200 hover:border-crimson/60 hover:bg-surface hover:shadow-lg hover:shadow-crimson/5 flex flex-col justify-between"
              >
                <div>
                  <div className="h-12 w-12 rounded-lg bg-crimson/15 border border-crimson/30 flex items-center justify-center text-crimson-light mb-4 group-hover:scale-105 transition-transform">
                    <Building2 className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 group-hover:text-crimson-light transition-colors">
                    Register as a Company
                  </h3>
                  <p className="text-xs text-neutral-400 leading-relaxed">
                    Set up your company workspace, register critical assets (APIs, repositories, infrastructure), and deploy autonomous AI security analysts.
                  </p>
                </div>

                <div className="mt-6 flex items-center text-xs font-mono font-semibold text-crimson group-hover:translate-x-1 transition-transform">
                  Configure Workspace & Assets <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                </div>
              </div>

              {/* Option 2: Register as an Employee */}
              <div
                onClick={() => {
                  setError(null);
                  setActiveBranch("employee");
                }}
                className="group relative cursor-pointer rounded-xl border border-border-subtle bg-surface/50 p-6 transition-all duration-200 hover:border-blue-500/60 hover:bg-surface hover:shadow-lg hover:shadow-blue-500/5 flex flex-col justify-between"
              >
                <div>
                  <div className="h-12 w-12 rounded-lg bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-blue-400 mb-4 group-hover:scale-105 transition-transform">
                    <Users className="h-6 w-6" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition-colors">
                    Register as an Employee
                  </h3>
                  <p className="text-xs text-neutral-400 leading-relaxed">
                    Find and join your organization&apos;s existing ShadowOps team. Collaborate on vulnerability triaging, attack paths, and security fixes.
                  </p>
                </div>

                <div className="mt-6 flex items-center text-xs font-mono font-semibold text-blue-400 group-hover:translate-x-1 transition-transform">
                  Search Company Directory <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2A: Register as a Company Form */}
        {activeBranch === "company" && (
          <Card className="animate-fadeIn border-border-subtle bg-surface/90">
            <CardHeader className="border-b border-border-subtle/60 pb-5">
              <div className="flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setError(null);
                    setActiveBranch("select");
                  }}
                  className="text-xs text-neutral-400 hover:text-white"
                >
                  <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
                  Change Selection
                </Button>
                <Badge variant="outline" className="border-crimson/50 text-crimson font-mono text-[10px]">
                  COMPANY ONBOARDING
                </Badge>
              </div>
              <CardTitle className="text-xl font-bold text-white mt-2">
                Setup Company & Assets
              </CardTitle>
              <CardDescription className="text-xs text-neutral-400">
                Provide your company profile and register your initial asset to activate continuous AI security monitoring.
              </CardDescription>
            </CardHeader>

            <CardContent className="pt-6">
              <form onSubmit={handleCompanySubmit} className="space-y-6">
                {/* Section 1: Company Profile */}
                <div className="space-y-4">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-crimson uppercase tracking-wider">
                    <Building2 className="h-4 w-4" />
                    <span>Company & Workspace Information</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Company Name <span className="text-crimson">*</span>
                      </label>
                      <Input
                        required
                        placeholder="e.g. Acme Cyber Labs"
                        value={companyName}
                        onChange={(e) => handleCompanyNameChange(e.target.value)}
                        className="bg-background text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Workspace Identifier (Slug)
                      </label>
                      <Input
                        placeholder="e.g. acme-cyber-labs"
                        value={slug}
                        onChange={(e) => setSlug(e.target.value)}
                        className="bg-background font-mono text-xs text-neutral-300"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Industry / Sector
                      </label>
                      <select
                        value={industry}
                        onChange={(e) => setIndustry(e.target.value)}
                        className="w-full h-10 px-3 rounded-md bg-background border border-border-subtle text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                      >
                        <option value="Fintech & Banking">Fintech & Banking</option>
                        <option value="SaaS & Cloud Platforms">SaaS & Cloud Platforms</option>
                        <option value="Healthcare & Life Sciences">Healthcare & Life Sciences</option>
                        <option value="E-commerce & Retail">E-commerce & Retail</option>
                        <option value="Cybersecurity & Defense">Cybersecurity & Defense</option>
                        <option value="AI & Machine Learning">AI & Machine Learning</option>
                        <option value="Enterprise IT">Enterprise IT</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Team Size
                      </label>
                      <select
                        value={teamSize}
                        onChange={(e) => setTeamSize(e.target.value)}
                        className="w-full h-10 px-3 rounded-md bg-background border border-border-subtle text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                      >
                        <option value="1-10">1-10 Employees</option>
                        <option value="11-50">11-50 Employees</option>
                        <option value="51-200">51-200 Employees</option>
                        <option value="201-1000">201-1000 Employees</option>
                        <option value="1000+">1000+ Employees</option>
                      </select>
                    </div>

                    <div className="md:col-span-2">
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Your Full Name (Workspace Owner)
                      </label>
                      <Input
                        placeholder="e.g. Alex Mercer"
                        value={ownerDisplayName}
                        onChange={(e) => setOwnerDisplayName(e.target.value)}
                        className="bg-background text-sm"
                      />
                    </div>
                  </div>
                </div>

                <div className="border-t border-border-subtle/60 pt-5 space-y-4">
                  {/* Section 2: Initial Asset Setup */}
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-crimson uppercase tracking-wider">
                    <Server className="h-4 w-4" />
                    <span>Primary Security Asset Setup</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Asset Name
                      </label>
                      <Input
                        placeholder="e.g. Core API Backend"
                        value={assetName}
                        onChange={(e) => setAssetName(e.target.value)}
                        className="bg-background text-sm"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Asset Type
                      </label>
                      <select
                        value={assetType}
                        onChange={(e) => setAssetType(e.target.value as AssetType)}
                        className="w-full h-10 px-3 rounded-md bg-background border border-border-subtle text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                      >
                        <option value="repository">Code Repository (GitHub / GitLab)</option>
                        <option value="api">API Endpoint / Microservice</option>
                        <option value="application">Web Application (Frontend / Fullstack)</option>
                        <option value="infrastructure">Cloud Infrastructure (AWS / GCP / Azure)</option>
                        <option value="container">Container & Kubernetes</option>
                      </select>
                    </div>

                    <div className="md:col-span-2">
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Asset Identifier / Target URL
                      </label>
                      <Input
                        placeholder="e.g. https://github.com/organization/core-app or https://api.company.com"
                        value={assetIdentifier}
                        onChange={(e) => setAssetIdentifier(e.target.value)}
                        className="bg-background font-mono text-xs text-neutral-300"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Environment
                      </label>
                      <select
                        value={assetEnvironment}
                        onChange={(e) => setAssetEnvironment(e.target.value)}
                        className="w-full h-10 px-3 rounded-md bg-background border border-border-subtle text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                      >
                        <option value="production">Production</option>
                        <option value="staging">Staging</option>
                        <option value="development">Development</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                        Criticality
                      </label>
                      <select
                        value={assetCriticality}
                        onChange={(e) => setAssetCriticality(e.target.value as AssetCriticality)}
                        className="w-full h-10 px-3 rounded-md bg-background border border-border-subtle text-neutral-200 text-sm focus:outline-none focus:border-crimson"
                      >
                        <option value="critical">Critical (Tier 1)</option>
                        <option value="high">High (Tier 2)</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="pt-2 flex justify-end space-x-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setActiveBranch("select")}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" disabled={submitting}>
                    {submitting ? (
                      <span className="flex items-center">
                        <LoadingSpinner size="sm" className="mr-2" /> Initializing Workspace...
                      </span>
                    ) : (
                      <span className="flex items-center">
                        <Sparkles className="h-4 w-4 mr-2" /> Complete Company Onboarding
                      </span>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* STEP 2B: Register as an Employee Form */}
        {activeBranch === "employee" && (
          <Card className="animate-fadeIn border-border-subtle bg-surface/90">
            <CardHeader className="border-b border-border-subtle/60 pb-5">
              <div className="flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setError(null);
                    setActiveBranch("select");
                  }}
                  className="text-xs text-neutral-400 hover:text-white"
                >
                  <ArrowLeft className="h-3.5 w-3.5 mr-1.5" />
                  Change Selection
                </Button>
                <Badge variant="outline" className="border-blue-500/50 text-blue-400 font-mono text-[10px]">
                  EMPLOYEE ONBOARDING
                </Badge>
              </div>
              <CardTitle className="text-xl font-bold text-white mt-2">
                Join an Existing Company
              </CardTitle>
              <CardDescription className="text-xs text-neutral-400">
                Enter your identity details and search the company directory to join your engineering team.
              </CardDescription>
            </CardHeader>

            <CardContent className="pt-6 space-y-6">
              {/* Employee Information */}
              <div className="space-y-4">
                <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">
                  <UserCheck className="h-4 w-4" />
                  <span>Your Employee Details</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                      Full Name <span className="text-crimson">*</span>
                    </label>
                    <Input
                      required
                      placeholder="e.g. Jane Doe"
                      value={employeeName}
                      onChange={(e) => setEmployeeName(e.target.value)}
                      className="bg-background text-sm"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-neutral-300 mb-1.5">
                      Job Title / Role
                    </label>
                    <Input
                      placeholder="e.g. Senior Security Engineer"
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      className="bg-background text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Directory Search & List */}
              <div className="border-t border-border-subtle/60 pt-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">
                    <Building2 className="h-4 w-4" />
                    <span>Company Directory</span>
                  </div>
                  <span className="text-[11px] font-mono text-neutral-400">
                    {companies.length} {companies.length === 1 ? "organization" : "organizations"} available
                  </span>
                </div>

                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-neutral-400" />
                  <Input
                    placeholder="Search company by name or slug..."
                    value={directorySearch}
                    onChange={(e) => setDirectorySearch(e.target.value)}
                    className="pl-9 bg-background text-sm"
                  />
                </div>

                {/* Company Cards List */}
                <div className="space-y-3 pt-2">
                  {searchingDirectory ? (
                    <div className="py-8 text-center flex flex-col items-center justify-center space-y-2">
                      <LoadingSpinner size="md" />
                      <span className="text-xs font-mono text-neutral-400">
                        Querying registered organizations...
                      </span>
                    </div>
                  ) : companies.length === 0 ? (
                    <div className="p-8 text-center rounded-lg border border-dashed border-border-subtle bg-surface/30">
                      <Building2 className="h-8 w-8 text-neutral-400 mx-auto mb-2 opacity-40" />
                      <div className="text-xs font-medium text-neutral-300">
                        No registered companies found
                      </div>
                      <div className="text-[11px] text-neutral-400 mt-1">
                        Try searching with a different keyword, or ask your administrator to register your company first.
                      </div>
                    </div>
                  ) : (
                    companies.map((company) => {
                      const isJoining = joiningCompanyId === company.id;
                      return (
                        <div
                          key={company.id}
                          className="flex items-center justify-between p-4 rounded-lg border border-border-subtle bg-surface/40 hover:bg-surface/80 transition-colors"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2">
                              <span className="text-sm font-bold text-white">
                                {company.name}
                              </span>
                              <Badge variant="outline" className="text-[10px] uppercase font-mono">
                                {company.plan || "Free"}
                              </Badge>
                            </div>
                            <div className="flex items-center space-x-3 text-xs text-neutral-400 font-mono">
                              <span>slug: /{company.slug}</span>
                              <span>•</span>
                              <span className="flex items-center">
                                <Users className="h-3 w-3 mr-1 text-neutral-400" />
                                {company.members_count} {company.members_count === 1 ? "member" : "members"}
                              </span>
                            </div>
                          </div>

                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={isJoining || !!joiningCompanyId || !employeeName.trim()}
                            onClick={() => handleJoinCompany(company)}
                            className="font-mono text-xs"
                          >
                            {isJoining ? (
                              <span className="flex items-center">
                                <LoadingSpinner size="sm" className="mr-1.5" /> Joining...
                              </span>
                            ) : (
                              <span className="flex items-center">
                                Join Team <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                              </span>
                            )}
                          </Button>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border-subtle py-4 px-6 text-center text-xs text-neutral-400 font-mono">
        ShadowOps AI-Assisted Security Operations Platform • Built with ShreyanshCodes
      </footer>
    </div>
  );
}
