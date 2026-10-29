# Baseline Capture & Evidence Comparison

## 1. Baseline Capture

Before verifying an applied fix, ShadowOps captures an authoritative baseline snapshot from the original scan finding and its associated evidence records.

### Snapshot Structure
```json
{
  "finding_id": "uuid",
  "rule_id": "python.jwt.hardcoded-jwt-secret",
  "file_path": "auth/tokens.py",
  "line_start": 42,
  "line_end": 44,
  "code_snippet": "JWT_SECRET = 'hardcoded-insecure-secret-key-123'",
  "snippet_hash": "sha256...",
  "fingerprint": "sha256...",
  "evidence_count": 1,
  "evidence_items": [...]
}
```

The `fingerprint` combines rule, file, line start, and trimmed snippet hash to prevent ambiguity.

---

## 2. Evidence Comparison Engine

The comparison engine [`EvidenceComparisonEngine`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/evidence_comparison_engine.py) matches findings produced during the independent post-patch rescan against the baseline.

### 2.1 Conservative Shift Matching
- Naive checkers declare a bug fixed if line 42 no longer triggers an alert.
- Real patches often add or remove lines (e.g., adding imports or wrapper functions), which shifts line numbers.
- [`EvidenceComparisonEngine`](file:///d:/Shreyanshcodes/shadow-ops-v2/backend/app/services/evidence_comparison_engine.py) uses a configurable `LINE_SHIFT_TOLERANCE` (default: 15 lines) combined with string and token similarity:
  - If the same `rule_id` is found in the same file with `abs(shift) <= 15` and `similarity >= 0.8`: categorized as **`STILL_PRESENT`**.
  - If the same `rule_id` is found in the same file beyond the shift tolerance: categorized as **`MODIFIED_OR_MOVED`**.

### 2.2 Regression Detection
- If a new, different rule violation appears in any of the patch's `affected_files`, the outcome is categorized as **`POSSIBLE_REGRESSION`**.
- This directly prevents patches that fix an injection flaw while simultaneously introducing unescaped `eval()` calls or insecure deserialization sinks.

### 2.3 Verified Elimination
- Only when zero rule violations are detected for the target rule in the target file, and no new regressions exist across the affected file boundary, is the state marked **`NO_LONGER_DETECTED`**.
