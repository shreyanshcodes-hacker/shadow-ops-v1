# SHADOWOPS — AI DATA HANDLING & COST CONTROLS
## Sanitization, Redaction, Caching & Token Management

```
+-----------------------------------------------------------------------------------+
|                        AI DATA HANDLING SPECIFICATION                             |
+-----------------------------------------------------------------------------------+
```

---

## 1. Sensitive Secret Redaction

Before code snippets or evidence payloads leave the backend boundary to external LLM providers (Gemini or Grok), they pass through `app.ai.safety.redact_secrets()`.

The redactor identifies and replaces the following secret categories with standardized placeholders:

| Sensitive Pattern | Redacted Placeholder | Defends Against |
|---|---|---|
| RSA/EC/OpenSSH Private Keys | `[REDACTED_PRIVATE_KEY]` | LLM ingestion of cryptographic signing keys |
| AWS Access Key IDs (`AKIA...`) | `[REDACTED_AWS_KEY_ID]` | Cloud credential leakage |
| AWS Secret Access Keys | `[REDACTED_AWS_SECRET]` | Cloud access compromise |
| Bearer Tokens & JWTs | `[REDACTED_BEARER_TOKEN]` | Session hijacking |
| Connection Strings with Passwords | `[REDACTED_PASSWORD]` | Database credential exfiltration |
| Generic Secrets & Passwords | `[REDACTED_SECRET]` | Hardcoded credential harvesting |

---

## 2. Deterministic Hash Deduplication & Caching

To prevent redundant LLM invocations and unnecessary API spend, the system calculates a deterministic SHA-256 fingerprint of the finding's analytical payload (`app.ai.cost.compute_input_hash`):

$$\text{input\_hash} = \text{SHA256}(\text{finding\_id} + \text{title} + \text{rule\_id} + \text{snippet} + \text{evidence} + \text{prompt\_version})$$

### Execution Logic:
1. When a scan analysis is requested with `force = False`:
   - The system checks if `FindingAIAnalysis` exists with matching `finding_id` and `input_hash`.
   - If a match is found, the LLM invocation is skipped and the cached analysis is reused immediately.
   - The response increments `findings_skipped_cached`.
2. When `force = True`:
   - A fresh LLM invocation is performed, updating the existing record and its timestamp.

---

## 3. Token & Character Budget Controls

1. **Context Truncation (`app.ai.cost.truncate_context`)**:
   - Code snippets are capped at `AI_MAX_INPUT_CHARS` (default: 12,000 characters).
   - If code exceeds this limit, it is cleanly truncated while preserving the top and bottom sections:
     `[... TRUNCATED X CHARACTERS FOR TOKEN BUDGET ...]`
2. **Batch Caps (`AI_MAX_FINDINGS_PER_RUN`)**:
   - Scans are limited to analyzing a maximum of 25 findings per single run to prevent runaway batch costs.
3. **Run Budget Ceiling (`AI_COST_CAP_PER_RUN_USD`)**:
   - Configurable per-run cost ceiling (default: \$2.00 USD).
4. **Persistent Spend Tracking**:
   - Token usage and estimated USD costs are tracked per run in `agent_runs` (`tokens_input`, `tokens_output`, `cost_usd`).
