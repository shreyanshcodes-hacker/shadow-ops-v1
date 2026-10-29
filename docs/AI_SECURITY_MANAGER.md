# SHADOWOPS — AI SECURITY MANAGER
## Architecture, Responsibilities & Operational Invariants

```
+-----------------------------------------------------------------------------------+
|                            AI SECURITY MANAGER                                    |
|                      Level 3 Advisory Security Analyst                            |
+-----------------------------------------------------------------------------------+
```

---

## 1. System Role & Scope

The **AI Security Manager** is the primary analytical intelligence component introduced in Stage 4. Its role is to bridge the gap between low-level AST scanner outputs (Semgrep findings) and human engineering decisions by providing structured, context-rich security analysis.

### Primary Responsibilities
1. **Explain Finding Mechanism**: Translates static pattern matches into technical explanations of root cause and execution flow.
2. **Contextualize Business Impact**: Evaluates how the weakness could affect confidentiality, integrity, availability, or regulatory compliance.
3. **Calibrate Confidence**: Assigns an objective confidence score (0.0 to 1.0) reflecting the clarity of evidence.
4. **Identify Uncertainty**: Explicitly documents assumptions, missing architectural context, or areas requiring runtime dynamic testing.
5. **Grounded Evidence Referencing**: Explicitly references only valid scanner evidence items.

---

## 2. Invariant Rules (Non-Negotiable)

1. **Advisory Authority Only**:
   - The AI Security Manager produces Level 3 advisory data. It **NEVER** mutates or overwrites scanner severities (`finding.severity`), scanner rule IDs (`finding.source_rule_id`), or source code locations.
2. **No Autonomous Infrastructure Changes**:
   - The AI Security Manager does not perform automated code refactoring, Git pushes, firewall modifications, or container redeployments in Stage 4.
3. **Evidence Anchoring**:
   - Any supporting evidence cited by the model must correspond to a verified `FindingEvidence` database row. Any hallucinated IDs are systematically stripped before persistence.
4. **Tenant Isolation**:
   - AI analyses are strictly isolated by `workspace_id` in PostgreSQL with enforced Row Level Security (RLS). Cross-workspace leakage is impossible.

---

## 3. Data Schema & Persistence

The AI analysis is stored in the `finding_ai_analysis` table:

| Column | Type | Description |
|---|---|---|
| `id` | `UUID PK` | Unique analysis identifier |
| `finding_id` | `UUID FK` | Unique 1-to-1 foreign key to `findings.id` |
| `ai_run_id` | `UUID FK` | Optional link to parent `agent_runs.id` |
| `workspace_id` | `UUID FK` | Multi-tenant workspace scoping |
| `summary` | `TEXT` | Executive summary of finding |
| `technical_explanation` | `TEXT` | In-depth root cause explanation |
| `impact` | `TEXT` | Operational and business impact |
| `confidence` | `NUMERIC(3,2)` | Score between 0.00 and 1.00 |
| `classification` | `TEXT` | Weakness classification (e.g. CWE family) |
| `uncertainty` | `TEXT` | Known assumptions or context gaps |
| `supporting_evidence` | `JSONB` | Array of verified evidence references |
| `model` | `TEXT` | LLM model identifier (e.g. `gemini-1.5-pro`) |
| `provider` | `TEXT` | AI provider (e.g. `gemini`, `grok`) |
| `prompt_version` | `TEXT` | Version string of prompt template (e.g. `v1.0`) |
| `input_hash` | `TEXT` | SHA-256 fingerprint of analytical input |
| `created_at` | `TIMESTAMPTZ`| Creation timestamp |
| `updated_at` | `TIMESTAMPTZ`| Last update timestamp |
