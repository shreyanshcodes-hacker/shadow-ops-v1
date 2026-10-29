# SHADOWOPS — RISK MODEL V1 SPECIFICATION
**Model Identifier:** `risk-v1`  
**Engine Type:** Deterministic Weighted Security Scoring  
**Output Scale:** 0.00 to 100.00 (Continuous, rounded to 2 decimal places)  

---

## 1. Mathematical Equation
$$\text{Score} = \min\left(100.00, \max\left(0.00, 0.30 \cdot S + 0.20 \cdot E + 0.20 \cdot A + 0.15 \cdot C + 0.10 \cdot X + 0.05 \cdot P\right)\right)$$

---

## 2. Dimension Weights and Inputs

### 2.1 Finding Severity ($S$) — Weight: 30%
Evaluates the core vulnerability severity of the attack chain:
- Base score: Maximum severity across path findings (`critical`=100.0, `high`=80.0, `medium`=50.0, `low`=25.0, `info`=10.0).
- Chain compounding bonus: Multi-step exploit chains compound defensive difficulty:
  $$\text{Bonus} = \min(15.0, \max(0.0, (\text{Node Count} - 1) \times 3.0))$$
- Final $S = \min(100.0, \text{Base} + \text{Bonus})$.

### 2.2 Exploitability ($E$) — Weight: 20%
Evaluates technical feasibility and barrier reduction:
- Base likelihood: Average likelihood of transitions across path edges.
- Relationship amplification multipliers:
  - If any edge is `ENABLES`, `EXPOSES`, or `EXPLOITS`: $+15\%$ multiplier.
  - If any edge is `AMPLIFIES` or `PRIVILEGE_ESCALATION`: $+10\%$ multiplier.
- Final $E = \min(100.0, \text{Base Likelihood} \times 100.0 \times \text{Multiplier})$.

### 2.3 Asset Criticality ($A$) — Weight: 20%
Evaluates business and architectural consequence of target compromise:
- `critical`: 100.0
- `high`: 75.0
- `medium`: 50.0
- `low`: 25.0

### 2.4 Confidence ($C$) — Weight: 15%
Evaluates empirical confidence of findings and relationships:
- Average confidence across all findings and relationship edges scaled to 0–100.

### 2.5 Exposure ($X$) — Weight: 10%
Evaluates attack accessibility from external perimeters:
- `public` / `external` / `internet_facing`: 90.0 – 100.0
- `internal` / `private`: 40.0
- `hybrid`: 70.0

### 2.6 Path Complexity ($P$) — Weight: 5%
Shallow, direct attack chains are significantly easier to exploit and pose higher immediate threat:
- $\le 2$ nodes: 95.0
- $3$ nodes: 80.0
- $4$ nodes: 65.0
- $\ge 5$ nodes: 50.0

---

## 3. Risk Bands
- `0.00 – 19.99`: **INFORMATIONAL**
- `20.00 – 39.99`: **LOW**
- `40.00 – 59.99`: **MEDIUM**
- `60.00 – 79.99`: **HIGH**
- `80.00 – 100.00`: **CRITICAL**

---

## 4. Invariant
> No external agent, LLM prompt, or user interface parameter can modify the formula or override the final calculated score.
