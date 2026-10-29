# SHADOWOPS — ATTACK PATH ARCHITECTURE
**Stage:** STAGE 6  
**Status:** IMPLEMENTED & LOCKED  

---

## 1. Objective & Architectural Role
The **Attack Path Engine** transforms isolated vulnerabilities discovered during scans into structured, multi-step exploit chains:

$$\text{Asset} \longrightarrow \text{Finding A} \xrightarrow{\text{ENABLES}} \text{Finding B} \xrightarrow{\text{EXPOSES}} \text{Finding C} \longrightarrow \text{Compromised Target}$$

Rather than treating each weakness in a vacuum, the engine establishes contextual transitions that represent realistic lateral movement, privilege escalation, and data exfiltration paths.

---

## 2. Core Security Invariant
> **"AI MAY SUGGEST RELATIONSHIPS. DETERMINISTIC CODE DECIDES THE FINAL SCORE."**
> - The AI is strictly advisory and cannot override scanner facts, database records, or calculated numerical risk scores.
> - Final risk scores are computed solely by deterministic backend logic based on explicit, auditable weights.

---

## 3. Data Model & Graph Entities

### 3.1 Security Relationships (`security_relationships`)
Represents directed connections between two distinct findings in the same workspace.
- `source_finding_id`: Finding initiating or enabling the transition.
- `target_finding_id`: Finding reached, exposed, or amplified.
- `relationship_type`: Allowlisted enum:
  - `DEPENDS_ON`: Target finding requires source finding to exist or be reachable first.
  - `ENABLES`: Source finding directly bypasses a trust boundary, granting access to target.
  - `EXPOSES`: Source finding reveals secrets, credentials, or network routes to target.
  - `LEADS_TO`: Natural attacker progression from source to target.
  - `SHARES_COMPONENT`: Both findings reside within the same software module or file.
  - `SHARES_ENTRY_POINT`: Both findings share an external interface or OWASP classification.
  - `SHARES_DATA_FLOW`: Tainted data from source flows into target sink.
  - `AMPLIFIES`: Co-location of both vulnerabilities significantly elevates threat severity.
- `source`:
  - `DETERMINISTIC`: Inferred by static heuristics (file paths, line proximity, CWE pairs).
  - `AI_SUGGESTED`: Suggested via structured LLM reasoning (`AIRelationshipSuggestion`).
  - `HUMAN_CONFIRMED`: Explicitly validated and endorsed by a human security operator.
- `status`: `active`, `confirmed`, `dismissed`.

### 3.2 Attack Path Entities (`attack_paths`, `attack_path_nodes`, `attack_path_edges`)
- `attack_paths`: Header tracking name, title, description, entry point, target asset, risk score, risk band, and model version.
- `attack_path_nodes`: Ordered nodes along the path with step index (`node_order`: 0, 1, 2, ...), vulnerability link, and risk contribution.
- `attack_path_edges`: Directed edges linking sequential nodes with transition type and likelihood.
- `risk_snapshots`: Auditable historical log of every risk score calculation for the path.

---

## 4. Graph Safety & Bounds
1. **Cycle Detection:** Depth-first search (DFS) with recursion stack tracking prevents infinite loops and self-referential chains ($A \to B \to A$).
2. **Length Boundary:** Maximum attack path length is strictly capped at `MAX_ATTACK_PATH_NODES = 8`.
3. **Workspace Isolation:** Every node and relationship must belong to the exact same tenant workspace. Cross-workspace traversal is structurally impossible and rejected with HTTP 403/404.
