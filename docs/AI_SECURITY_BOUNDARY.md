# SHADOWOPS — AI SECURITY BOUNDARY SPECIFICATION
## Authoritative Facts vs Advisory Interpretation & Security Isolation

```
+-----------------------------------------------------------------------------------+
|                        AI SECURITY BOUNDARY SPECIFICATION                         |
+-----------------------------------------------------------------------------------+
```

---

## 1. Absolute Separation: Facts vs Interpretation

A fundamental architectural principle of ShadowOps is that **AI output is NOT trusted application control data**.

| Dimension | Scanner Finding (Ground Truth) | AI Security Analysis (Advisory) |
|---|---|---|
| **Authority Level** | Level 1 & 2 (Authoritative) | Level 3 (Advisory Interpretation) |
| **Origin** | Deterministic Semgrep rule match on AST | Probabilistic LLM evaluation |
| **Severity Field** | `finding.severity` (Immutable by AI) | `finding_ai_analysis.severity_assessment` |
| **File Location** | `finding.location` (`file`, `line_start`) | Extracted context (Read-only) |
| **Lifecycle State** | `finding.status` (`open`, `fixed`, etc.) | `finding_ai_analysis.status` (`SUCCEEDED`) |
| **Modification Rights** | Human security lead / triage action | Read-only advisory display |

---

## 2. Model Output Sandboxing

Model output is strictly informational and cannot directly trigger:
- Shell commands or terminal subprocesses
- Repository commits, branch creation, or pull requests
- Infrastructure modifications, DNS changes, or deployments
- Finding status mutations or false-positive closures
- Role elevation or workspace access changes
- Network egress or outbound scanning probes

Any future automated action system must have an explicit, human-authorized approval boundary.

---

## 3. Multi-Tenant Workspace Boundary

AI analyses are strictly partitioned by tenant:
1. Every `finding_ai_analysis` row contains `workspace_id` referencing `workspaces.id`.
2. PostgreSQL Row Level Security (RLS) ensures that tenant users can only read analyses where they hold active membership in `workspace_members`.
3. Backend service endpoints (`/api/v1/findings/{id}/ai-analysis`, `/api/v1/ai-analyses/{id}`) independently verify caller workspace membership using `WorkspaceService.get_workspace(...)`. Guessing or enumerating UUIDs results in immediate HTTP 403/404 rejection.
