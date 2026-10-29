# SHADOWOPS — STAGE 6 BASELINE REPORT
**Date:** 2026-10-26  
**Stage:** STAGE 6 — ATTACK PATH INTELLIGENCE & DETERMINISTIC RISK ENGINE  
**Baseline Status:** VERIFIED & LOCKED  

---

## 1. Baseline Verification Summary
- **Backend Tests:** 39 passed in 2.64s (`pytest backend/tests -v`).
- **Frontend Codebase:** Clean Next.js 14 App Router, TypeScript strict checks pass, ESLint passes with 0 errors.
- **Architectural Isolation:** Full workspace multi-tenancy enforced across all entities (assets, scans, findings, evidence, AI analyses).
- **Core Safety Invariant:** `NO AUTHORIZATION -> NO SCAN` strictly preserved.

---

## 2. Stage 6 Target Scope & Objectives
1. **Security Relationships:**
   - Define deterministic correlation signals: same asset, same file, nearby lines, shared CWE/OWASP category, shared software component.
   - Introduce structured AI relationship suggestions via `AI_SUGGESTED` source with bounded relationship types (`DEPENDS_ON`, `ENABLES`, `EXPOSES`, `LEADS_TO`, `SHARES_COMPONENT`, `SHARES_ENTRY_POINT`, `SHARES_DATA_FLOW`, `AMPLIFIES`).
   - Human confirmation workflow (`HUMAN_CONFIRMED` or dismissed).
2. **Deterministic Risk Engine (Model `risk-v1`):**
   - Pure, reproducible risk scoring (0–100 scale) based on weighted factors:
     - Finding Severity: 30%
     - Exploitability / Reachability: 20%
     - Asset Criticality & Business Impact: 20%
     - Confidence: 15%
     - Exposure / External Entry Point: 10%
     - Path Complexity / Step Length: 5%
   - Explicit Risk Bands:
     - `INFORMATIONAL`: 0–19
     - `LOW`: 20–39
     - `MEDIUM`: 40–59
     - `HIGH`: 60–79
     - `CRITICAL`: 80–100
   - **Crucial Invariant:** "AI MAY SUGGEST RELATIONSHIPS. DETERMINISTIC CODE DECIDES THE FINAL SCORE." The AI and client UI never dictate or override the numerical risk score.
3. **Attack Path Construction & Graph Safety:**
   - Directed acyclic graph traversal with cycle prevention.
   - Bound path length (`MAX_ATTACK_PATH_NODES = 8`).
   - Strictly workspace-isolated nodes and edges.
4. **Database & API Layer:**
   - `security_relationships` and `risk_snapshots` tables + migrations.
   - Attack path and relationship REST endpoints with role-based access control.
   - Full audit logging for relationship suggestions, confirmations, and risk recalculations.
5. **Frontend Command Center:**
   - `/attack-paths` listing page.
   - `/attack-paths/[id]` visual + accessible step-by-step graph inspection and risk factor breakdown.
   - Finding detail integration showing related findings and participating paths.
   - Dashboard widget displaying real active attack paths and risk metrics.

---

## 3. Implementation Plan
- Step 1: Baseline Audit (Completed)
- Step 2: Database Migration & SQLAlchemy Models
- Step 3: Core Correlation, Graph, and Risk Engines
- Step 4: REST API Endpoints & Audit Logging
- Step 5: Backend Automated Unit & Security Test Suite
- Step 6: Frontend Attack Path UI & Dashboard Integration
- Step 7: Validation, Architecture Documentation & Final Stage 6 Report
