# ShadowOps Release-Readiness Policy & Evaluation Framework

## 1. Release Policy Objectives

This document establishes the official governance policy for determining whether ShadowOps may be deployed to production environments. In compliance with strict cybersecurity engineering principles, **a passing local build or successful test suite alone is never sufficient for production certification.**

---

## 2. Release Outcome Classifications

Every release evaluation must conclude with one of three explicit, mutually exclusive decisions:

### Outcome A: NOT READY
The software must **not** be deployed to any shared environment or customer-facing infrastructure.
**Trigger Conditions (any one will trigger this state):**
- Any open **CRITICAL** or **HIGH** severity security defect.
- Any failing automated test in the core test suite.
- Unhandled secret leaks in logs, reports, or API responses.
- Inability to enforce workspace multi-tenancy isolation.
- Vulnerabilities allowing unauthenticated remote code execution or unauthorized scan execution.
- Missing database rollback or migration failure on clean deployment.

---

### Outcome B: READY FOR CONTROLLED PILOT
The software is authorized for deployment to an isolated, invitation-only pilot environment with designated early-adopter customers under direct engineering supervision.
**Mandatory Criteria:**
- **Zero** open CRITICAL or HIGH severity defects in core code.
- 100% passing hermetic unit, integration, and security test suites.
- Application-level multi-tenant isolation rigorously verified for all assets, scans, findings, attack paths, remediations, verifications, reports, and notifications.
- Human-in-the-loop governance invariants enforced:
  - Scans require validated authorization.
  - Patch application strictly requires signed human approval bound to the SHA256 patch hash.
  - Finding closure strictly requires verified evidence comparison and human review sign-off.
- AI cannot override scanner evidence or risk formulas.
- Secret redaction verified in reports, exports, and event payloads.
- **Accepted Limitations in Pilot:**
  - Live external services (e.g., Live Firebase Auth token verification with Google, live Supabase PostgreSQL RLS, live SMTP, live n8n webhook targets) that cannot be verified without customer-specific cloud credentials must be explicitly marked **UNVERIFIED** and operated under monitored supervisory controls.
  - Pilot customers must be informed that email delivery may operate in degraded in-app mode unless SMTP credentials are provided.

---

### Outcome C: READY FOR PRODUCTION
The software is certified for general availability (GA), self-service onboarding, and mission-critical production workloads.
**Mandatory Criteria (all of Outcome B PLUS):**
- Complete live end-to-end integration verified against dedicated production-tier cloud environments:
  - Live Firebase Authentication tenant verified with real token revocation and email verification checks.
  - Live Supabase PostgreSQL database verified with active Row Level Security (RLS) policies enforcing database-tier multi-tenancy.
  - Live SMTP/transactional email provider verified with DKIM/SPF delivery validation.
  - Live AI providers (Gemini/Grok) load-tested with token quotas and rate limiting.
  - Production backup and point-in-time recovery (PITR) successfully restored and tested in rehearsal.
  - Zero critical supply-chain vulnerabilities in unpinned dependencies.
  - Full observability stack (APM, distributed tracing, alerting, SIEM export) operational.

---

## 3. Decision Matrix for Current Stage 12 Evaluation

Based on the repository audit and test execution:

| Evaluation Dimension | Verification State | Pilot Eligibility | Production GA Eligibility |
| :--- | :--- | :--- | :--- |
| **Hermetic Core Test Suite** | 92/92 tests passing (100%) | **PASS** | **PASS** |
| **Workspace & Multi-Tenancy Isolation** | Application-level checks verified across all endpoints | **PASS** | **PASS** |
| **Patch & Remediation Safety** | Hash binding, rollback checkpoints, human approval gate | **PASS** | **PASS** |
| **Verification & Finding Closure Gate** | Rescan + regression + evidence + human reviewer required | **PASS** | **PASS** |
| **Secret Sanitization** | Recursive redaction in reports, PDF/JSON, event envelopes | **PASS** | **PASS** |
| **Controlled Workflows & n8n** | Allowlist enforced, n8n disabled by default, SSRF blocked | **PASS** | **PASS** |
| **Frontend Production Compilation** | Clean Next.js build across 21 routes | **PASS** | **PASS** |
| **Live Firebase Auth with Google Cloud** | Test tokens validated hermetically; Live Google API unverified | **PASS (Supervised)** | **UNVERIFIED (Blocker)** |
| **Live Supabase PostgreSQL RLS** | Schema & migrations validated; Live RLS engine unverified locally | **PASS (Supervised)** | **UNVERIFIED (Blocker)** |
| **Live SMTP Email Provider** | Safe degraded fallback verified; Real mailbox delivery unverified | **PASS (Degraded)** | **UNVERIFIED (Blocker)** |
| **Automated Off-site Backups & PITR** | Disaster recovery runbook documented; live restore unverified | **PASS (Runbook)** | **UNVERIFIED (Blocker)** |

### Formal Decision:
**RECOMMENDATION: READY FOR CONTROLLED PILOT**  
*(Deployment to general production GA is restricted until live cloud dependencies—Firebase, Supabase RLS, and live SMTP—are validated in the staging environment).*
