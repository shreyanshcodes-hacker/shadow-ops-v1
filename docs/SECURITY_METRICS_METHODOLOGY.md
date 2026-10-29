# ShadowOps — Security Metrics & Calculation Methodology (Stage 10)

## 1. Principles of Security Posture Calculation

ShadowOps enforces strict mathematical reproducibility for all displayed and reported security metrics.

### 1.1 Invariant: Distinguishing Missing Data from Zero Risk
A common trap in startup security tooling is reporting "0 vulnerabilities" or "Low Risk" when in reality no scans have been performed.
In ShadowOps:
- If `scans.completed == 0`:
  - `has_completed_scans` is explicitly set to `False`.
  - `data_disclaimer` is generated: `NO COMPLETED SCANS: This workspace has not completed any vulnerability scans. Zero detected vulnerabilities does not mean the perimeter is secure.`
  - `risk.is_calculated` is `False`.
  - `risk.risk_band` displays `UNSCANNED` or `NOT_CALCULATED`.

### 1.2 Deterministic Risk Score (`risk-v1`)
The workspace risk score is computed deterministically in Stage 6 using the formula:
$$\text{Score} = \min\left(100.0, \, \sum w_i \cdot F_i + \text{Impact}_{\text{AttackPaths}}\right)$$

- Base finding severity weights:
  - Critical: $25.0$
  - High: $15.0$
  - Medium: $5.0$
  - Low: $1.0$
- Active Attack Path Multiplier:
  - Critical attack path (unmitigated, traversable): $+20.0$ each.
- Risk Bands:
  - $80.0 \le \text{Score} \le 100.0 \implies \text{CRITICAL}$
  - $60.0 \le \text{Score} < 80.0 \implies \text{HIGH}$
  - $30.0 \le \text{Score} < 60.0 \implies \text{MEDIUM}$
  - $0.0 \le \text{Score} < 30.0 \implies \text{LOW}$

**AI agents and LLMs have ZERO mathematical authority over this numerical score.**

---

## 2. 30-Day Trend Windows & Time-Series Methodology

The dashboard trend calculation divides the previous $N$ days (default: 30) into discrete calendar-day buckets in UTC.

### 2.1 Findings Velocity
For each day $d$:
- $\text{New}(d)$: Findings with $(\text{first\_seen\_at} \lor \text{created\_at})$ on day $d$.
- $\text{Fixed}(d)$: Findings with $\text{fixed\_at}$ on day $d$.
- $\text{Open}(d)$: Cumulative findings active on day $d$:
  $$\text{Open}(d) = \{ f \in \text{Findings} \mid \text{created\_at} \le d \land (\text{fixed\_at} \text{ is NULL} \lor \text{fixed\_at} > d) \}$$

### 2.2 Fix Verification Velocity
- A proposal is counted as **Applied** only when an approved patch has been physically applied to the codebase with a recorded git commit hash and rollback checkpoint.
- A proposal is counted as **Verified** only when an independent Stage 9 verification job has completed with a verdict of `VERIFIED_CANDIDATE` and evidence comparison of `NO_LONGER_DETECTED`.
- A finding is marked `fixed` in the database only after a human reviewer with Admin/Owner role signs off on the verification review.
