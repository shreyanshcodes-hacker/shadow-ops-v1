# SHADOWOPS — AI SECURITY TEAM (STAGE 7)

## 1. Overview & Positioning

ShadowOps provides an **AI Security Team** designed for startups and modern engineering teams. 
Rather than a monolithic prompt or single chatbot, the team operates as a syndicate of **5 specialized analytical workers** that collaboratively analyze authorized security data:

```
[Authorized Asset Perimeter]
           ↓
[Controlled Scan & Semgrep Analysis]
           ↓
[Normalized Findings & Evidence]
           ↓
[Deterministic Relationship Graph & Risk Engine (risk-v1)]
           ↓
┌─────────────────────────────────────────────────────────────┐
│                 SHADOWOPS AI SECURITY TEAM                  │
│                                                             │
│   1. RECON_AGENT             (Perimeter & Exposed Surfaces) │
│              ↓                                              │
│   2. VULNERABILITY_ANALYST   (Mechanisms & Preconditions)   │
│              ↓                                              │
│   3. ATTACK_PATH_AGENT       (Multi-Hop Chains & Transitions)│
│              ↓                                              │
│   4. RISK_ANALYST            (Deterministic Factor Context) │
│              ↓                                              │
│   5. SECURITY_REVIEWER       (Consensus & Executive Brief)  │
└─────────────────────────────────────────────────────────────┘
           ↓
[Team Assessment: review_status = "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"]
           ↓
[Mandatory Human-in-the-Loop Review & Sign-Off Boundary]
```

---

## 2. The 5 Specialized Security Agents

### 1. RECON_AGENT (`recon-v1`)
- **Role**: Perimeter Architect & Boundary Analyst.
- **Scope**: Evaluates asset repository metadata, components, exposure boundaries, entry points, and structural layout.
- **Safety Invariant**: Strictly bounded to authorized asset perimeter. Never performs active network reconnaissance or port probing against unauthorized domains.
- **Contract Schema**: `ReconOutput` (`relevant_components`, `entry_points`, `security_boundaries`, `exposed_areas`, `uncertainty`, `observations`).

### 2. VULNERABILITY_ANALYST_AGENT (`vulnerability-analyst-v1`)
- **Role**: Vulnerability Mechanic & Precondition Specialist.
- **Scope**: Performs deep analysis of individual findings, code snippets, and AST matches. Explains exact attacker preconditions, blast radius, and missing verification evidence.
- **Safety Invariant**: Analytical only. Never writes exploit payloads or proof-of-concept scripts. Cannot alter scanner severity or status.
- **Contract Schema**: `VulnerabilityAnalystOutput` (`findings_analyzed`, `interpretations`, `uncertainty`).

### 3. ATTACK_PATH_AGENT (`attack-path-v1`)
- **Role**: Exploit Chain & Path Analyst.
- **Scope**: Examines relationships between vulnerabilities (`ENABLES`, `EXPOSES`, `SHARES_COMPONENT`) and analyzes how isolated weaknesses connect into practical exploit progressions.
- **Safety Invariant**: AI may suggest candidate transitions, but the deterministic graph service remains authoritative for graph topology and path synthesis.
- **Contract Schema**: `AttackPathAnalystOutput` (`candidate_relationships`, `path_observations`, `confidence`, `missing_evidence`, `explanation`, `uncertainty`).

### 4. RISK_ANALYST_AGENT (`risk-analyst-v1`)
- **Role**: Contextual Risk & Business Impact Explainer.
- **Scope**: Explains the factors behind the deterministic `risk-v1` calculation (criticality, exposure, compounded findings, attack path multiplier) and highlights human triage priorities.
- **Safety Invariant**: Under NO circumstances can the risk analyst mutate, downgrade, or recalculate the deterministic risk score. The score is authoritative and audited.
- **Contract Schema**: `RiskAnalystOutput` (`deterministic_score_reference`, `risk_band`, `explanation`, `important_contributing_factors`, `uncertainty`, `recommended_human_review_priorities`).

### 5. SECURITY_REVIEWER_AGENT (`security-reviewer-v1`)
- **Role**: Executive Synthesizer & Quality Gatekeeper.
- **Scope**: Ingests outputs from all 4 upstream agents, checks for consensus and conflicting observations, evaluates remaining uncertainties, and drafts a unified Team Assessment.
- **Safety Invariant**: The reviewer must enforce the mandatory human review boundary: `review_status = "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"`. The agent cannot approve changes or dismiss risks.
- **Contract Schema**: `TeamAssessment` (`review_status`, `executive_summary`, `key_security_concerns`, `highest_priority_findings`, `highest_priority_attack_paths`, `risk_interpretation`, `uncertainties`, `conflicting_assessments`, `recommended_human_actions`, `overall_confidence`, `evidence_references`).

---

## 3. Human-in-the-Loop Review Boundary

The core principle of ShadowOps Stage 7 is that **AI agents are analytical workers, not autonomous operators**.

1. **Advisory Output**: Every team evaluation run is marked with:
   ```json
   "review_status": "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED"
   ```
2. **Review Endpoint**: Human engineers must explicitly sign off on assessments:
   ```http
   POST /api/v1/security-team/runs/{run_id}/review?workspace_id={workspace_id}
   Content-Type: application/json

   {
     "notes": "Reviewed with engineering lead. SQL injection confirmed and patch PR scheduled."
   }
   ```
3. **Audit Persistence**: Every review captures `reviewed_by` (profile UUID), `reviewed_at` (UTC timestamp), and `review_notes` in the database and audit trail.
