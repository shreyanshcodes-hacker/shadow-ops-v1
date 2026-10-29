# SHADOWOPS — DETERMINISTIC RISK ENGINE
**Stage:** STAGE 6  
**Status:** IMPLEMENTED & LOCKED  

---

## 1. Philosophical Principle
The core security law governing ShadowOps risk intelligence is:

> **AI MAY SUGGEST RELATIONSHIPS.**  
> **DETERMINISTIC CODE DECIDES THE FINAL SCORE.**

Security decisions, compliance thresholds, and vulnerability prioritizations cannot rely on non-deterministic LLM score generation. While LLMs excel at qualitative pattern recognition and unstructured code comprehension, they are prone to numeric hallucination, non-reproducibility, and drift.

Therefore:
- LLM outputs produce advisory data (`AI_SUGGESTED` relationships, qualitative rationales).
- The numerical risk score is computed by a pure, deterministic mathematical engine.
- Given identical inputs, the engine produces mathematically identical scores every single time down to two decimal places.

---

## 2. Mathematical Model: `risk-v1`
The risk score $R$ is scaled continuously between $0.00$ and $100.00$:

$$R = \min(100.00, \max(0.00, \sum_{i=1}^{6} (w_i \times s_i)))$$

Where:
$$\sum_{i=1}^{6} w_i = 0.30 + 0.20 + 0.20 + 0.15 + 0.10 + 0.05 = 1.00$$

### Factor Breakdown:
| Factor | Weight ($w_i$) | Scale ($s_i$) | Derivation Heuristic |
|---|---|---|---|
| **Finding Severity** | 30% ($0.30$) | 0–100 | Highest severity among path nodes (`critical`=100, `high`=80, `medium`=50, `low`=25, `info`=10) plus chain compounding bonus: $\min(15, (\text{nodes} - 1) \times 3)$ |
| **Exploitability** | 20% ($0.20$) | 0–100 | Average edge transition likelihood scaled by relationship amplification factor (+15% for `ENABLES`/`EXPOSES`, +10% for `AMPLIFIES`) |
| **Asset Criticality** | 20% ($0.20$) | 0–100 | Business impact tier of target asset (`critical`=100, `high`=75, `medium`=50, `low`=25) |
| **Confidence** | 15% ($0.15$) | 0–100 | Average confidence level across contributing scanner findings and relationship linkages |
| **Exposure** | 10% ($0.10$) | 0–100 | Target asset perimeter exposure (`external`/`public`=90–100, `internal`=40) |
| **Path Complexity** | 5% ($0.05$) | 0–100 | Short, direct attack chains are easier to traverse and execute ($\le 2$ nodes = 95, 3 nodes = 80, 4 nodes = 65, $5+$ nodes = 50) |

---

## 3. Deterministic Risk Bands
Every calculated score maps to an auditable risk band:

| Score Range | Risk Band | Recommended Action |
|---|---|---|
| **80.00 – 100.00** | `CRITICAL` | Immediate mitigation; blocks deployments |
| **60.00 – 79.99** | `HIGH` | High priority remediation required within current sprint |
| **40.00 – 59.99** | `MEDIUM` | Triage and schedule for next release cycle |
| **20.00 – 39.99** | `LOW` | Normal maintenance queue |
| **0.00 – 19.99** | `INFORMATIONAL` | Defensive hardening guidance only |

---

## 4. Auditability & Snapshot Persistence
Whenever an attack path is synthesized or recalculated:
1. All contributing factors with individual scores, weights, and contributions are serialized to JSON.
2. A permanent, immutable record is stored in `risk_snapshots`.
3. An audit log event (`RISK_CALCULATED`) is recorded with the user ID, previous score, and new score.
