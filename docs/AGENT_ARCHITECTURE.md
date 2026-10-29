# AGENT ARCHITECTURE — SHADOWOPS

## 1. Multi-Agent Design Specification

ShadowOps employs 8 purpose-built, specialized security agents orchestrated by the AI Security Manager. Each agent operates with a discrete operational boundary, typed input/output schemas, deterministic retry logic, and strict evidence provenance.

---

## 2. Detailed Agent Specifications

---

### 1. Recon Agent
- **Responsibilities**: Analyzes target external perimeter, open ports, exposed headers, DNS records, TLS certificates, and API discovery endpoints. Filters noise and identifies exposed attack surfaces.
- **Model Selection**: **Google Gemini 1.5 Flash** (high token processing speed, low cost for bulk JSON log processing).
- **Inputs**: Target URL/hostname, port scan summaries, DNS TXT/A records, TLS handshake metadata, HTTP response headers.
- **Outputs**: Normalized perimeter inventory, discovered public API endpoints, misconfigured security headers (HSTS, CSP, CORS), and perimeter exposure score.
- **Schema**: `ReconOutputSchema` (endpoints, exposed_services, perimeter_vulnerabilities, exposure_rating).
- **Execution Order**: Phase 1 (Runs in parallel with Code Security & Dependency Agents).
- **Evidence Requirements**: Raw HTTP response headers, DNS query records, TLS certificate chain metadata.
- **Confidence Rating**: Scored 0.0 to 1.0 based on deterministic header matching.
- **Failure Handling & Retry Strategy**: Up to 2 retries on network timeout; on persistent failure, marks recon phase as partial and logs warning.
- **Cost Controls**: Capped at 50,000 input tokens; truncated header lists.

---

### 2. Code Security Agent
- **Responsibilities**: Ingests raw Semgrep SAST SARIF reports, locates source code snippets, analyzes AST call chains, performs taint tracking verification, and separates true positives from false alarms.
- **Model Selection**: **Google Gemini 1.5 Pro** (exceptional code comprehension across multi-language codebases and massive context window).
- **Inputs**: Semgrep findings JSON/SARIF, referenced source code files, framework context (Django, FastAPI, Express, Spring).
- **Outputs**: Validated code vulnerabilities, false-positive dismissals with justifications, taint flow descriptions, CWE classifications, and code-level evidence references.
- **Schema**: `CodeSecurityOutputSchema` (confirmed_findings, discarded_findings, taint_paths).
- **Execution Order**: Phase 1 (Parallel).
- **Evidence Requirements**: Exact file path, line numbers, vulnerable function definition, input source, and unescaped sink code snippet.
- **Confidence Rating**: Scored 0.0 to 1.0; findings with confidence < 0.60 are marked for manual triage.
- **Failure Handling & Retry Strategy**: 1 retry with reduced code window if context exceeds limits; falls back to raw Semgrep findings if model fails.
- **Cost Controls**: Capped at 150,000 input tokens per scan; prioritizes high/critical severity Semgrep matches.

---

### 3. Dependency Agent
- **Responsibilities**: Analyzes software composition (SCA), parses package manifests (`package-lock.json`, `poetry.lock`, `go.sum`, `pom.xml`), cross-references CVE/GHSA advisories, and detects transitive vulnerability chains.
- **Model Selection**: **Google Gemini 1.5 Flash**.
- **Inputs**: Dependency manifest files, lockfiles, package dependency trees, advisory database matches.
- **Outputs**: Direct vs. transitive vulnerability mappings, exploitability context (e.g. is the vulnerable function actually imported/invoked in user code?), and upgrade path recommendations.
- **Schema**: `DependencyOutputSchema` (vulnerable_packages, reachable_functions, cve_references, safe_upgrade_versions).
- **Execution Order**: Phase 1 (Parallel).
- **Evidence Requirements**: Exact package name, installed version, fixed version, dependency chain trace.
- **Confidence Rating**: High (0.90+) for direct lockfile matches; calculated reachability score for usage analysis.
- **Failure Handling & Retry Strategy**: 2 retries with exponential backoff on rate limits.
- **Cost Controls**: Summarizes dependency trees; skips dev-dependencies unless explicitly requested.

---

### 4. Threat Analyst
- **Responsibilities**: Synthesizes perimeter recon, code vulnerabilities, and dependency flaws into unified attack vectors. Reasons like an adversary to determine realistic breach scenarios and attack paths.
- **Model Selection**: **xAI Grok** (strong adversary simulation, exploit feasibility reasoning) with **Gemini 1.5 Pro** fallback.
- **Inputs**: Validated findings from Recon, Code Security, and Dependency agents; asset criticality ratings; network exposure topology.
- **Outputs**: Realistic exploit scenarios, multi-step attack chains, prerequisite conditions, and blast radius assessments.
- **Schema**: `ThreatAnalysisOutputSchema` (attack_scenarios, entry_nodes, target_nodes, chained_finding_ids, prerequisite_steps).
- **Execution Order**: Phase 2 (Follows Phase 1 finding normalization).
- **Evidence Requirements**: Must reference valid `finding_id`s from Phase 1.
- **Confidence Rating**: Evaluated based on prerequisite feasibility (e.g., requires valid login vs. unauthenticated remote execution).
- **Failure Handling & Retry Strategy**: Failover to Gemini 1.5 Pro if Grok API is unavailable.
- **Cost Controls**: Token cap at 60,000 tokens; max 5 synthesized scenarios per scan.

---

### 5. Risk Analyst
- **Responsibilities**: Evaluates contextual exploitability, business exposure, and asset criticality to supply verified inputs into the deterministic risk engine. Explains the risk calculation in plain business and technical terms.
- **Model Selection**: **xAI Grok / Google Gemini 1.5 Pro**.
- **Inputs**: Threat scenarios, asset criticality, network reachability, finding severity, public exploit database flags.
- **Outputs**: Qualitative risk justifications, exploitability multipliers (0.0 - 1.0), and contextual risk explanations.
- **Schema**: `RiskAnalysisOutputSchema` (exploitability_assessment, exposure_rating, blast_radius_impact, risk_explanation).
- **Execution Order**: Phase 3 (Precedes final mathematical risk score calculation).
- **Evidence Requirements**: References threat scenarios and finding IDs.
- **Confidence Rating**: Bound to evidence availability.
- **Failure Handling & Retry Strategy**: Default to baseline CVSS metrics if Risk Analyst fails.
- **Cost Controls**: Standard structured prompts; 30,000 token limit.

---

### 6. Remediation Agent
- **Responsibilities**: Produces precise, non-destructive remediation proposals. For code flaws, generates unified diffs; for dependencies, produces lockfile bump commands; for infra, outputs secure configuration templates.
- **Model Selection**: **Google Gemini 1.5 Pro** (ensures syntax correctness, preserves code formatting and idiomatic styles).
- **Inputs**: Target finding, original source snippet, language AST context, dependency versions, framework documentation.
- **Outputs**: Unified patch diff, human-readable fix explanation, potential side effects, prerequisite steps, and verification instructions.
- **Schema**: `RemediationOutputSchema` (diff_content, file_path, fix_type, side_effects_analysis, verification_command).
- **Execution Order**: Phase 4 (Post-risk scoring).
- **Evidence Requirements**: Direct line/character references to vulnerable source code.
- **Confidence Rating**: Code patches undergo automated AST parsing checks before being marked valid (ensures generated code is syntactically correct).
- **Failure Handling & Retry Strategy**: Re-prompts model if generated diff fails `patch --dry-run` or syntax linting.
- **Cost Controls**: Runs only on high and critical findings by default, or upon user request.

---

### 7. Verification Agent
- **Responsibilities**: Inspects applied fixes, formulates verification strategies (re-scan parameters, reproduction payloads), and verifies that vulnerabilities have been eradicated without regressions.
- **Model Selection**: **xAI Grok / Google Gemini 1.5 Flash**.
- **Inputs**: Original finding details, applied remediation diff, post-remediation code/asset state, re-scan results.
- **Outputs**: Empirical verification assessment (`passed`, `failed`, `inconclusive`), regression analysis, and residual risk score.
- **Schema**: `VerificationOutputSchema` (verification_status, evidence_comparison, regression_detected, rationale).
- **Execution Order**: Phase 5 (Triggered after human-authorized remediation is applied).
- **Evidence Requirements**: Re-scan Semgrep output (showing absence of rule violation) or HTTP response showing 401/403/sanitized output.
- **Confidence Rating**: Requires 100% empirical evidence; never assumes fix worked without re-test.
- **Failure Handling & Retry Strategy**: Retries verification scan up to 2 times.
- **Cost Controls**: Focused, lightweight context (under 20,000 tokens).

---

### 8. Reporting Agent
- **Responsibilities**: Synthesizes all scan metadata, findings, verified remediations, and attack paths into comprehensive executive, compliance (SOC 2 / ISO 27001), and technical reports.
- **Model Selection**: **Google Gemini 1.5 Flash**.
- **Inputs**: Workspace security posture data, scan events, finding records, risk scores, attack path graphs.
- **Outputs**: Structured Markdown and JSON reports formatted for PDF compilation and board presentations.
- **Schema**: `ReportOutputSchema` (executive_summary, key_risks, compliance_status, remediation_progress, detailed_findings).
- **Execution Order**: Phase 6 (Final stage).
- **Evidence Requirements**: Sourced from actual database records.
- **Confidence Rating**: 1.0 (Direct reporting based on verified database tables).
- **Failure Handling & Retry Strategy**: 1 retry with simplified template if document assembly fails.
- **Cost Controls**: Standardized templated prompts.

---

## 3. Agent Coordination & Lifecycle Matrix

| Agent | Model | Phase | Timeout | Max Retries | Token Budget | Schema Contract |
|---|---|---|---|---|---|---|
| **Recon** | Gemini Flash | Phase 1 | 60s | 2 | 50,000 | `ReconOutputSchema` |
| **Code Security** | Gemini Pro | Phase 1 | 180s | 1 | 150,000 | `CodeSecurityOutputSchema` |
| **Dependency** | Gemini Flash | Phase 1 | 90s | 2 | 80,000 | `DependencyOutputSchema` |
| **Threat Analyst** | Grok / Gemini Pro | Phase 2 | 120s | 1 | 60,000 | `ThreatAnalysisOutputSchema` |
| **Risk Analyst** | Grok / Gemini Pro | Phase 3 | 90s | 1 | 30,000 | `RiskAnalysisOutputSchema` |
| **Remediation** | Gemini Pro | Phase 4 | 180s | 2 | 100,000 | `RemediationOutputSchema` |
| **Verification** | Grok / Gemini Flash| Phase 5 | 120s | 2 | 40,000 | `VerificationOutputSchema` |
| **Reporting** | Gemini Flash | Phase 6 | 90s | 1 | 50,000 | `ReportOutputSchema` |
