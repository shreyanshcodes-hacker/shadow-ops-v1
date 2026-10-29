# SHADOWOPS — AI RELATIONSHIP ANALYSIS
**Stage:** STAGE 6  
**Status:** IMPLEMENTED & LOCKED  

---

## 1. Overview
The **AI Relationship Analysis** engine is an advisory component that evaluates pairs of security findings within the same workspace to infer subtle, contextual vulnerability transitions that pure static heuristics might miss.

---

## 2. Structural Prompt Fencing & Injection Defense
Untrusted finding fields (titles, descriptions, scanner rule excerpts) are wrapped in strict structural tags and sanitized prior to LLM submission:

```
<security_analysis_context>
Analyze the following two security findings for contextual relationships.

<finding_a>
Finding ID: {id}
Title: {redacted_title}
Severity: {severity}
CWEs: {cwes}
OWASP: {owasp}
Description: {redacted_description}
</finding_a>

<finding_b>
Finding ID: {id}
Title: {redacted_title}
Severity: {severity}
CWEs: {cwes}
OWASP: {owasp}
Description: {redacted_description}
</finding_b>

Determine if finding A and finding B exhibit any of the allowed security relationships.
</security_analysis_context>
```

---

## 3. Strict Schema & Allowlist Enforcement
The AI is bound to a Pydantic schema: `AIRelationshipSuggestion`.
Returned relationship types are validated against the strict allowlist:
- `DEPENDS_ON`
- `ENABLES`
- `EXPOSES`
- `LEADS_TO`
- `SHARES_COMPONENT`
- `SHARES_ENTRY_POINT`
- `SHARES_DATA_FLOW`
- `AMPLIFIES`

If an unallowed relationship type is returned, or if confidence is below 0.40, the suggestion is rejected.

---

## 4. Human-in-the-Loop Confirmation
- All AI suggestions are tagged with `source = 'AI_SUGGESTED'` and `status = 'active'`.
- Security operators can confirm a relationship (`POST /api/v1/relationships/{id}/confirm`), which sets `source = 'HUMAN_CONFIRMED'`, records `confirmed_by = user_id`, and adds an audit trail entry.
- False correlations can be dismissed (`POST /api/v1/relationships/{id}/dismiss`).
