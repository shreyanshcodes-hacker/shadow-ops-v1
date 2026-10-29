# RISK ARCHITECTURE — SHADOWOPS

## 1. Deterministic Risk Model Principles

The ShadowOps Risk Engine calculates vulnerability risk through a **strictly deterministic, auditable mathematical formula**. 

### Core Constraints
1. **No AI Score Invention**: AI models are strictly forbidden from fabricating, hallucinating, or arbitrarily assigning final numeric scores. AI agents provide structured qualitative evaluations (exploitability assessments, reachability verification, blast radius), which feed as constrained numeric variables into a deterministic formula.
2. **Explainability**: Every calculated score must be broken down into discrete weighted components stored in `risk_assessments.factor_breakdown`.
3. **Repeatability**: Given the identical set of input attributes, the engine will always produce the exact same score.
4. **Normalized Scale**: All scores and factors are bounded between $0.00$ and $100.00$.

---

## 2. Risk Factors & Weight Matrix

The total risk score for any finding is a composite of six weighted factors:

$$\text{Final Risk Score} = \sum_{i=1}^{6} (F_i \times W_i)$$

Where:

| Factor ($F_i$) | Description | Weight ($W_i$) | Scale | Source |
|---|---|:---:|:---:|---|
| **$F_{\text{sev}}$: Base Severity** | Intrinsic technical severity of the vulnerability type (CVSS-aligned) | **30%** (0.30) | 0 – 100 | Semgrep rule severity / CVSS base |
| **$F_{\text{exp}}$: Exploitability** | Practical ease of weaponization and exploit availability | **20%** (0.20) | 0 – 100 | CVE exploit-db presence, AI reachability assessment |
| **$F_{\text{net}}$: Network Exposure** | Reachability of the flaw from external untrusted networks | **15%** (0.15) | 0 – 100 | Recon Agent / Asset network configuration |
| **$F_{\text{crit}}$: Asset Criticality** | Business value and sensitivity of the compromised asset | **15%** (0.15) | 0 – 100 | User-defined asset classification |
| **$F_{\text{path}}$: Attack Path Impact** | Blast radius amplification if the finding is part of a chained breach path | **10%** (0.10) | 0 – 100 | Attack Path Correlation Engine |
| **$F_{\text{conf}}$: Finding Confidence** | Statistical confidence that the finding is a true positive | **10%** (0.10) | 0 – 100 | Tool confidence + Code Security Agent verification |

$$\sum W_i = 0.30 + 0.20 + 0.15 + 0.15 + 0.10 + 0.10 = 1.00 \text{ (100\%)}$$

---

## 3. Factor Calculations & Value Mapping

### 3.1 Base Severity Score ($F_{\text{sev}}$)
Mapped from standardized severity classifications:
- **Critical**: 95.0
- **High**: 75.0
- **Medium**: 50.0
- **Low**: 25.0
- **Info**: 10.0

*Note: If a formal CVSS v3.1 base score ($0.0 - 10.0$) is supplied via CVE metadata, $F_{\text{sev}} = \text{CVSS} \times 10.0$.*

### 3.2 Exploitability Score ($F_{\text{exp}}$)
Calculated algorithmically:
$$\text{Baseline} = 50.0$$
- $+ 30.0$ if known public exploit exists (Exploit-DB, Metasploit, CISA KEV catalog).
- $+ 15.0$ if unauthenticated exploitation is possible.
- $- 20.0$ if non-standard user interaction or administrative privileges are required.
- $- 15.0$ if strong defensive mitigations (ASLR, WAF, strict input types) are detected.
$$\text{Bounded to } [0.0, 100.0]$$

### 3.3 Network Exposure Score ($F_{\text{net}}$)
Determined by perimeter accessibility:
- **Directly Internet-Facing / Public API**: 100.0
- **DMZ / Authenticated Web Portal**: 70.0
- **Internal Microservice / Private VPC**: 40.0
- **Air-gapped / Local Development Only**: 10.0

### 3.4 Asset Criticality Score ($F_{\text{crit}}$)
Defined by the asset classification in `assets.criticality`:
- **Critical** (Production DB, Customer PII, Auth Server): 100.0
- **High** (Core API, Payment Gateway Integration): 75.0
- **Medium** (Internal Admin Tool, Staging Environment): 50.0
- **Low** (Marketing site, Documentation portal, Dev sandbox): 20.0

### 3.5 Attack Path Impact ($F_{\text{path}}$)
Derived from graph reachability:
- $100.0$ if the finding is an entry-point node or critical bottleneck directly linking to a crown-jewel asset in an active `attack_path`.
- $60.0$ if part of an intermediate multi-hop path.
- $0.0$ if an isolated finding with no chained reachability.

### 3.6 Finding Confidence ($F_{\text{conf}}$)
- **High Confidence** (Semgrep deterministic rule match + AI AST validation confirmed): 100.0
- **Medium Confidence** (Heuristic rule match or pattern detection): 70.0
- **Low Confidence** (Potential match requiring manual verification): 40.0

---

## 4. Concrete Calculation Example

Consider an **Unauthenticated SQL Injection** discovered in an API endpoint:
- $F_{\text{sev}} = 95.0$ (Critical) $\times 0.30 = 28.5$
- $F_{\text{exp}} = 80.0$ (Public PoC available, no auth required) $\times 0.20 = 16.0$
- $F_{\text{net}} = 100.0$ (Public Internet endpoint) $\times 0.15 = 15.0$
- $F_{\text{crit}} = 100.0$ (Production API connected to customer database) $\times 0.15 = 15.0$
- $F_{\text{path}} = 100.0$ (Direct bridge to crown jewel database in attack graph) $\times 0.10 = 10.0$
- $F_{\text{conf}} = 100.0$ (Semgrep taint-mode confirmed sink) $\times 0.10 = 10.0$

$$\text{Final Risk Score} = 28.5 + 16.0 + 15.0 + 15.0 + 10.0 + 10.0 = \mathbf{94.50} \text{ (Critical Risk)}$$

---

## 5. Storage & Transparency in Database

The full calculation is preserved in `risk_assessments`:
```json
{
  "formula_version": "v1.0",
  "final_score": 94.50,
  "weights": {
    "severity": 0.30,
    "exploitability": 0.20,
    "exposure": 0.15,
    "criticality": 0.15,
    "attack_path": 0.10,
    "confidence": 0.10
  },
  "raw_factors": {
    "severity": 95.0,
    "exploitability": 80.0,
    "exposure": 100.0,
    "criticality": 100.0,
    "attack_path": 100.0,
    "confidence": 100.0
  },
  "weighted_contributions": {
    "severity": 28.5,
    "exploitability": 16.0,
    "exposure": 15.0,
    "criticality": 15.0,
    "attack_path": 10.0,
    "confidence": 10.0
  }
}
```
This payload enables the UI to render an interactive **Risk Factor Breakdown Modal**, allowing developers and auditors to inspect the exact math behind every score.
