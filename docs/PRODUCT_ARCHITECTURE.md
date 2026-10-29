# PRODUCT ARCHITECTURE — SHADOWOPS

## 1. Product Definition & Mission

**ShadowOps** is an AI-native cybersecurity SaaS platform designed specifically for startups, high-growth engineering organizations, and security teams. It operates as an autonomous, always-vigilant **AI Security Team**, bridging the critical gap between complex, noisy legacy security scanners and resource-constrained engineering organizations.

### Tagline
> **"Your AI Security Team. Always Watching."**

### Core Promise
ShadowOps delivers continuous, end-to-end security lifecycle management across authorized applications, source code repositories, cloud infrastructure, and APIs through an unbroken 8-stage operational loop:

$$\text{DISCOVER} \longrightarrow \text{ANALYZE} \longrightarrow \text{CORRELATE} \longrightarrow \text{PRIORITIZE} \longrightarrow \text{EXPLAIN} \longrightarrow \text{REMEDIATE} \longrightarrow \text{VERIFY} \longrightarrow \text{REPORT}$$

1. **DISCOVER**: Continuous mapping of attack surfaces, cloud assets, exposed API endpoints, open source dependencies, and codebases.
2. **ANALYZE**: Multi-agent static code analysis (SAST via Semgrep), software composition analysis (SCA), and reconnaissance.
3. **CORRELATE**: Synthesizing isolated vulnerabilities into interconnected, graph-based attack paths to expose true attacker reachability.
4. **PRIORITIZE**: Deterministic, explainable mathematical risk scoring based on real exploitability, asset criticality, network exposure, and blast radius.
5. **EXPLAIN**: Grounded contextual AI explanations citing concrete evidence, eliminating security jargon and hallucinated panic.
6. **REMEDIATE**: Generating production-ready, syntax-valid remediation proposals (code diffs, dependency upgrades, infrastructure configurations) requiring explicit human approval.
7. **VERIFY**: Empirical re-testing and validation to confirm vulnerabilities are resolved and regressions avoided before closing issues.
8. **REPORT**: Producing tailored executive summaries, compliance evidence (SOC 2, ISO 27001), and developer-actionable technical briefs.

---

## 2. The Non-Negotiable Security Boundary

> **NO AUTHORIZATION $\longrightarrow$ NO SCAN**

ShadowOps strictly adheres to ethical security and legal compliance standards:
- **Absolute Backend Enforcement**: Authorization checks are performed solely by the Python backend service before any scan job, worker dispatch, or network reconnaissance is triggered.
- **Frontend Untrusted**: The frontend UI is treated as completely untrusted presentation state. Disabling buttons, UI badges, or client-side checks offers zero security guarantee.
- **Verification Proofs**: Every asset must have an active, validated authorization record (DNS TXT verification, HTTP token response, verified OAuth repository ownership, or cryptographically signed enterprise agreement) before any inspection action occurs.
- **Zero Third-Party Targeting**: ShadowOps will fail closed and abort any operation targeting external hostnames or repositories lacking verified proof of ownership or permission.

---

## 3. Target User Personas & Value Matrix

| Persona | Core Challenges | Primary Product Needs | ShadowOps Value Proposition |
|---|---|---|---|
| **Startup Founders** | Cannot afford a dedicated CISO or \$200k+ AppSec engineer; need to pass enterprise customer security reviews and investor due diligence. | Clear security posture score, zero-overhead automated audits, investor-ready executive reports. | Provides a 24/7 AI Security Team out of the box, continuously improving security scores and generating audit-ready compliance summaries. |
| **Chief Technology Officers (CTOs)** | Overwhelmed by alert fatigue and hundreds of trivial scanner warnings; lack visibility into true business risk and attacker paths. | Business-aligned risk prioritization, attack path visualization, team velocity protection. | Chains individual flaws into deterministic attack graphs, showing exactly which 3 critical vulnerabilities lead to the customer database. |
| **Engineering Teams** | Context switching, unclear vulnerability descriptions, friction when security blocks CI/CD deployments. | Non-blocking workflows, clear developer-level explanations, seamless git integration. | Embeds actionable security guidance directly into their workflow with automated git branches and pull request proposals. |
| **Security Engineers** | Drowning in triage, manual evidence collection, writing repetitive remediation tickets, and validating fixes. | Evidence provenance, custom Semgrep rule execution, attack path exploration, automated verification. | Automates 80% of routine triage and evidence gathering, providing deep AST inspection and automated regression tests. |
| **Software Developers** | Unsure how to remediate complex cryptographic or injection flaws; fear breaking production when updating libraries. | Exact file/line citations, contextual code diffs, minimal dependency breaking changes. | Generates ready-to-review unified diffs and precise syntax repairs tailored to their existing codebase conventions. |
| **DevOps & Platform Teams** | Cloud misconfigurations, public exposure of internal services, secrets leaked into build pipelines. | Infrastructure-as-Code checks, network boundary mapping, secret scanning, CI/CD pipeline webhooks. | Continuously checks infrastructure definitions, monitors external attack surfaces, and alerts instantly via n8n integrations. |
| **Security Consultants & MSSPs** | Managing multiple client organizations with strict regulatory isolation requirements and custom reporting needs. | Strict multi-tenant workspace isolation, client-scoped assets, tamper-evident audit logs, white-label exports. | Rigid workspace boundaries, comprehensive audit trails, and customizable report generation per engagement. |

---

## 4. The 21-Step Core Product Lifecycle

The complete operational loop of ShadowOps flows deterministically through 21 distinct phases:

```
 1. USER AUTHENTICATES (Firebase Auth JWT issued)
    │
 2. USER ENTERS OR CREATES WORKSPACE (Multi-tenant tenant isolation verified)
    │
 3. USER ADDS AN ASSET (Repo, Public API, Cloud Infra, Web Application)
    │
 4. USER PROVIDES/RECORDS AUTHORIZATION (DNS TXT, HTTP header, OAuth token, signed agreement)
    │
 5. SHADOWOPS VALIDATES AUTHORIZATION (Backend verifies ownership/permission; fails closed)
    │
 6. SCAN BEGINS (Scan job queued, state transitioned to RUNNING)
    │
 7. RECON / SECURITY ANALYSIS OCCURS (Network surface, DNS, TLS, exposed headers mapped)
    │
 8. CODE / DEPENDENCY ANALYSIS OCCURS (Semgrep AST analysis, lockfile parsing)
    │
 9. AI SECURITY MANAGER COORDINATES AGENTS (Recon, Code, Dependency, Threat, Risk agents)
    │
10. FINDINGS ARE GENERATED (Normalized into unified vulnerability schema)
    │
11. EVIDENCE IS COLLECTED (SARIF, code snippets, HTTP transcripts stored in Supabase)
    │
12. FINDINGS ARE CORRELATED (Cross-asset relationship linking)
    │
13. RISK IS CALCULATED (Deterministic mathematical scoring: 0.0 - 100.0)
    │
14. ATTACK PATHS ARE CONSTRUCTED (Directed acyclic graph of threat reachability)
    │
15. AI GENERATES REMEDIATION (Patch diffs, dependency bump recipes, config updates)
    │
16. HUMAN APPROVES REMEDIATION (Mandatory human review; decision logged immutably)
    │
17. FIX APPLIED VIA EXPLICITLY AUTHORIZED WORKFLOW (PR created or patch downloaded)
    │
18. VERIFICATION RUNS (Empirical re-scan, reproduction testing, regression check)
    │
19. SECURITY SCORE IS RECALCULATED (Reflects verified remediation)
    │
20. REPORTS ARE GENERATED (Executive, Technical, and Scan reports compiled)
    │
21. AI SECURITY CHAT EXPLAINS RESULTS (Contextual RAG grounded in workspace evidence)
```

---

## 5. Architectural Non-Negotiables & Principles

1. **Human-in-the-Loop for All Actions**: The AI Security Manager proposes; authenticated humans authorize; the system executes. No automated destructive mutations occur.
2. **Evidence Provenance**: Every finding must retain its underlying cryptographic or AST evidence. Hallucinated findings without concrete evidence are automatically pruned.
3. **Deterministic Risk**: Risk scoring is algorithmic and explainable. AI models provide analytical context, but never invent numerical scores arbitrarily.
4. **Complete Data Isolation**: All database operations and storage objects are strictly partitioned by `workspace_id` through Row Level Security (RLS) policies.
