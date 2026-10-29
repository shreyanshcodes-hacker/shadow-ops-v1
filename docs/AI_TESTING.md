# SHADOWOPS — AI TESTING SPECIFICATION
## Verification Matrix, Security Invariant Validation & Test Execution

```
+-----------------------------------------------------------------------------------+
|                           AI TESTING SPECIFICATION                                |
+-----------------------------------------------------------------------------------+
```

---

## 1. Test Suite Architecture

The Stage 4 AI test suite is located in `backend/tests/` and executes hermetically with zero external network dependencies:

| Test File | Target Subsystem | Key Verification |
|---|---|---|
| `test_ai_abstraction.py` | Provider Abstraction | Gemini & Grok structured output schema generation and agent lifecycle states. |
| `test_ai_security_manager.py` | AI Security Manager & APIs | Secret redaction, prompt fencing, hallucination stripping, cost/hash caching, scan AI analysis API, and workspace isolation. |
| `test_ai_cannot_override_trusted_security_facts.py` | Mandatory Invariant | Proves that under adversarial downgrade attempts, scanner severity, rule ID, snippet, location, and scan status remain unmodified. |

---

## 2. Invariant Proof: `test_ai_cannot_override_trusted_security_facts.py`

This test directly validates the architectural guarantee:
$$\text{Finding.severity}_{\text{post-AI}} \equiv \text{Finding.severity}_{\text{pre-AI}}$$

### Test Execution Steps:
1. An authorized scan and a `critical` severity Semgrep finding with attached AST evidence are created in PostgreSQL/SQLite.
2. An adversarial mock AI provider returns an advisory summary claiming the finding is negligible (`confidence: 0.15`, classification `"Informational Notice"`), along with a fabricated evidence ID (`non-existent-fabricated-id-123`).
3. The AI Security Manager processes the finding and writes the advisory analysis to `finding_ai_analysis`.
4. The test verifies:
   - `finding.severity` in the database is strictly `"critical"` (UNMODIFIED).
   - `finding.source` remains `"semgrep"`.
   - `finding.source_rule_id` remains unchanged.
   - `finding.code_snippet` and `finding.location` remain unchanged.
   - The hallucinated evidence ID is stripped from `supporting_evidence`.
   - The advisory data is stored exclusively in `FindingAIAnalysis`.

---

## 3. Test Command & Results

```powershell
backend\venv\Scripts\python.exe -m pytest -o pythonpath=backend backend/tests -v
```

### Result:
- Total Tests: 31 passed
- Failures: 0
- Execution Time: 2.91 seconds
