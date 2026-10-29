# SHADOWOPS — AI SECURITY ANALYST ARCHITECTURE
## Stage 5: Structured Finding Analysis, Evidence Interpretation & Human-in-the-Loop Review

```
+-----------------------------------------------------------------------------------+
|                              AI SECURITY ANALYST                                  |
|                 Structured Security Finding Evaluation Engine                     |
+-----------------------------------------------------------------------------------+
```

---

## 1. System Mission & Core Boundaries

The **AI Security Analyst** is an analytical decision-support component designed to consume normalized findings and trusted evidence from Stage 4 and produce structured, evidence-grounded security analysis for human review.

```
       AUTHORIZED ASSET
              ↓
        CONTROLLED SCAN
              ↓
           SEMGREP
              ↓
      NORMALIZED FINDINGS
              ↓
       TRUSTED EVIDENCE
              ↓
      AI SECURITY ANALYST
              ↓
     STRUCTURED ANALYSIS
  (Observed / Inferred / Uncertain)
              ↓
        HUMAN REVIEW
```

### Prohibited Autonomous Capabilities (Non-Negotiable)
The AI is an **ANALYST**, not an autonomous security operator. It must **NOT**:
- Authorize or trigger scans autonomously
- Exploit vulnerabilities
- Modify code, configuration, or repositories
- Change finding status or declare a vulnerability fixed
- Generate or automatically apply patches/PRs
- Deploy code or modify infrastructure
- Approve remediation proposals
- Overrule or overwrite authoritative scanner facts

---

## 2. Structured Output Schema (`SecurityAnalysis`)

Every AI response must strictly conform to the typed `SecurityAnalysis` contract (`app.ai.schemas.SecurityAnalysis`):

```json
{
  "summary": "Executive summary of the vulnerability",
  "vulnerability_type": "Normalized security weakness type (e.g., Insecure Deserialization)",
  "severity_assessment": "critical | high | medium | low | info",
  "confidence": 0.95,
  "exploitability_assessment": "Evaluation of ease of exploitability and exposure",
  "impact_assessment": "Assessment of data, operational, and business risk",
  "affected_component": "Target file, endpoint, or module",
  "attack_preconditions": "Prerequisites for an attacker to achieve exploitation",
  "evidence_interpretation": {
    "observed": ["Directly observed scanner facts and line spans"],
    "inferred": ["Logical deductions regarding exploitability"],
    "uncertain": ["Missing context, reachability assumptions, or test requirements"]
  },
  "reasoning": "Step-by-step technical explanation linking evidence to risk",
  "recommended_next_steps": "Actionable guidance for a human security reviewer",
  "uncertainty": "Summary of primary uncertainties or limits of static analysis",
  "supporting_evidence": [
    {
      "evidence_id": "UUID-of-verified-evidence",
      "relevance": "Why this evidence supports the conclusion",
      "quote_or_reference": "Exact code or AST reference"
    }
  ]
}
```

---

## 3. Mandatory 3-Way Evidence Categorization

The AI Security Analyst is required to explicitly categorize its interpretation into three distinct dimensions:

1. **OBSERVED**:
   - Strictly factual data verified by the deterministic scanner (e.g., "Semgrep detected rule `python.lang.security.deserialization.pickle` at line 105 of `api/views.py`").
2. **INFERRED**:
   - Engineering deductions made by the model based on code patterns (e.g., "Untrusted input passed to `pickle.loads` can permit arbitrary code execution if reachable").
3. **UNCERTAIN**:
   - Context gaps that cannot be resolved solely from static AST matching (e.g., "Whether an upstream WAF or gateway validates message payloads prior to invocation").

---

## 4. Multi-Analysis Versioning & Persistence

Findings can be analyzed multiple times over their lifecycle (e.g., comparing Gemini vs Grok, or evaluating prompt updates). The system preserves complete historical provenance in the `finding_ai_analysis` table:

- Every analysis record is immutable and uniquely identified by `id`.
- Records store the specific `provider`, `model`, `prompt_version`, `input_hash`, `tokens_input`, `tokens_output`, `cost_usd`, `created_by`, and `status` (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`).
- The frontend exposes a version switcher to inspect historical assessments over time.
