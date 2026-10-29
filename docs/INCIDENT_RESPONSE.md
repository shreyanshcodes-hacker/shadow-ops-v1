# ShadowOps Incident Response Plan & Runbooks

**Document Version:** 1.0  
**Phase:** Stage 12 Production Hardening  
**Target Audience:** Security Operations, On-Call Engineers, Platform SRE  

---

## 1. Incident Severity Classification

| Severity | Definition | Response SLA | Escalation / Notification |
| :---: | :--- | :---: | :--- |
| **P1 — Critical** | Confirmed cross-tenant data leak, unauthorized code execution, remote code execution in scanner sandbox, or secret key exposure. | **< 15 minutes** | Immediate page to Lead Security Engineer, CTO, and affected workspace owners. |
| **P2 — Major** | Full scan engine outage, DB connection exhaustion, broken verification engine, or sustained failure of the event outbox. | **< 1 hour** | On-call platform engineer and engineering lead. |
| **P3 — Moderate** | AI agent timeouts, SMTP alert delivery degradation (falling back to in-app), or false-positive flood from an updated rule. | **< 4 hours** | Next-business-day triage or working hours response. |
| **P4 — Minor** | UI visual glitch, export formatting inconsistency, or non-blocking trend chart display bug. | **< 24 hours** | Standard backlog grooming. |

---

## 2. Containment Runbooks

### Runbook 1: Suspected Cross-Tenant Data Access
- **Symptoms:** User reports seeing findings or assets from another company, or audit logs show `403` / `404` spikes with mismatched workspace IDs.
- **Immediate Containment Actions:**
  1. Revoke the suspected user's session in Firebase Console or via Firebase Admin SDK.
  2. Inspect structured audit logs:
     ```bash
     SELECT * FROM audit_logs 
     WHERE workspace_id != actor_workspace_id 
     ORDER BY created_at DESC LIMIT 50;
     ```
  3. Verify application-level filtering in the offending endpoint.
  4. If Supabase RLS is suspected, enable strict RLS enforcement check:
     ```sql
     ALTER TABLE findings FORCE ROW LEVEL SECURITY;
     ```
  5. Preserve forensic snapshot of audit logs before taking services offline.

---

### Runbook 2: Unauthorized Scan Execution or Scanner Abuse
- **Symptoms:** Scanner running against an IP or repository without valid verified authorization, or abnormal scan request frequency.
- **Immediate Containment Actions:**
  1. Terminate running scan worker processes:
     ```bash
     pkill -f "semgrep"
     ```
  2. Invalidate the asset authorization record:
     ```sql
     UPDATE asset_authorizations 
     SET status = 'revoked', updated_at = NOW() 
     WHERE asset_id = '[TARGET_ASSET_ID]';
     ```
  3. Mark active scan records as failed:
     ```sql
     UPDATE scans 
     SET status = 'failed', error_message = 'Terminated by Security Incident Response: Authorization Revoked' 
     WHERE status = 'running' AND asset_id = '[TARGET_ASSET_ID]';
     ```
  4. Review who triggered the scan in `audit_logs`.

---

### Runbook 3: Malicious Remediation Proposal or Patch Hash Tampering
- **Symptoms:** Patch content does not match the approved SHA256 hash, or patch attempts to touch files outside approved boundaries.
- **Immediate Containment Actions:**
  1. Automated safety gates in `PatchApplicationAdapter` will reject the patch automatically with `PatchApplicationException: Hash mismatch`.
  2. If a patch was maliciously approved, transition proposal status immediately:
     ```sql
     UPDATE remediation_proposals 
     SET status = 'REJECTED', failure_reason = 'Incident Response Containment: Suspected Malicious Diff' 
     WHERE id = '[PROPOSAL_ID]';
     ```
  3. If patch was already applied, trigger rollback:
     ```bash
     POST /api/v1/remediations/{proposal_id}/rollback
     ```
  4. Verify checkpoint restoration was successful and repository matches base git commit.

---

### Runbook 4: Outbox Poison Queue Buildup
- **Symptoms:** High number of entries in `event_outbox` with `status = 'failed'` or `status = 'poison_quarantined'`.
- **Immediate Containment Actions:**
  1. Check readiness probe: `GET /api/v1/health/ready` (inspects outbox backlog).
  2. Query quarantined events:
     ```sql
     SELECT id, event_type, failure_reason, retry_count 
     FROM event_outbox 
     WHERE status = 'poison_quarantined' 
     ORDER BY created_at DESC;
     ```
  3. Identify if the failure is due to an invalid SMTP credential or broken webhook endpoint.
  4. Disable failing integration temporarily:
     ```bash
     export N8N_ENABLED=false
     ```
  5. Once fixed, re-queue events for retry:
     ```sql
     UPDATE event_outbox 
     SET status = 'pending', retry_count = 0 
     WHERE status = 'poison_quarantined';
     ```

---

## 3. Forensic Evidence Gathering & Post-Mortem

Following any P1 or P2 incident:
1. Export immutable audit logs for the incident window.
2. Preserve container logs and trace IDs from `X-Request-ID` headers.
3. Conduct a blameless post-mortem within 48 hours documenting:
   - Root cause analysis (5 Whys).
   - Detection time (MTTD) and resolution time (MTTR).
   - Corrective actions and regression test additions.
