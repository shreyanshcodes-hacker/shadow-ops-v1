# Delivery Failure Recovery & Outbox Operations Runbook

## 1. Overview of Failure Modes

In distributed cybersecurity SaaS platforms, event delivery failures generally fall into three categories:

1. **Transient Network Errors:** Intermittent DNS failures, timeouts, rate limits (HTTP 429), or temporary third-party API downtime.
2. **Configuration Deficits:** Missing or expired SMTP credentials, invalid webhook recipient URLs, or disabled external integrations.
3. **Poison Messages:** Malformed event payloads or data schema anomalies that cause repeated unhandled processing exceptions.

---

## 2. Exponential Backoff & Retry Logic

When an event processing or delivery failure occurs:
1. `EventOutbox.attempts` is incremented by 1.
2. If `attempts < max_attempts` (default 5):
   - Status remains `failed`.
   - The next attempt timestamp is calculated using exponential backoff:
     $$\text{backoff\_seconds} = 2^{\text{attempts}} \times 10\text{ seconds}$$
     - Attempt 1: 20 seconds
     - Attempt 2: 40 seconds
     - Attempt 3: 80 seconds
     - Attempt 4: 160 seconds
3. During scheduled or triggered outbox sweeps (`POST /events/outbox/process`), only events where `next_retry_at <= utc_now` are retried.

---

## 3. Poison Message Quarantine

If an outbox entry fails after 5 successive attempts:
- The system automatically transitions its state to `quarantined`.
- A critical log entry `outbox_event_quarantined_poison_pill` is emitted.
- The event is excluded from subsequent automated polling batches to prevent resource starvation.

---

## 4. Operator Recovery Procedures

### 4.1 Inspecting Quarantined Events
Query the `event_outbox` table for quarantined items:

```sql
SELECT id, workspace_id, event_type, attempts, error_message, created_at
FROM event_outbox
WHERE status = 'quarantined'
ORDER BY created_at DESC;
```

### 4.2 Reprocessing After Upstream Resolution
Once the root cause (e.g., SMTP credential refresh or firewall rule fix) has been resolved, operators can reset quarantined events to `pending`:

```sql
UPDATE event_outbox
SET status = 'pending',
    attempts = 0,
    next_retry_at = NULL,
    error_message = NULL
WHERE status = 'quarantined';
```

### 4.3 Triggering an Immediate Outbox Sweep
To trigger an on-demand batch run without waiting for periodic background tasks:

```bash
curl -X POST "http://localhost:8000/api/v1/events/outbox/process?batch_size=50" \
     -H "Authorization: Bearer <ADMIN_BEARER_TOKEN>"
```

### 4.4 Workflow Run Manual Retries
For failed controlled workflow actions:
1. Review the run details and error message in the **Workflows** page (`/workflows`) or via `GET /workflows/runs`.
2. Click **Retry** on the interface or execute:

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/runs/<RUN_ID>/retry?workspace_id=<WORKSPACE_ID>" \
     -H "Authorization: Bearer <ADMIN_BEARER_TOKEN>"
```
