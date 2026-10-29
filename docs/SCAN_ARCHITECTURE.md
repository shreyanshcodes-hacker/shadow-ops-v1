# SCAN ARCHITECTURE — SHADOWOPS

## 1. Controlled Scan Pipeline Overview

The ShadowOps scan engine operates as a deterministic, multi-phase state machine. Every scan progresses through an explicit series of validation, discovery, analysis, synthesis, and correlation phases.

```
                      [ SCAN_REQUESTED ]
                              │
                              ▼
                    [ AUTHORIZATION_CHECK ] ──(Unverified)──► [ SCAN_ABORTED ]
                              │ (Verified)
                              ▼
                     [ ASSET_VALIDATION ] ──(Invalid Target)► [ SCAN_FAILED ]
                              │ (Valid Target)
                              ▼
                        [ SCAN_CREATED ]
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
         [ RECON ]                      [ CODE_ANALYSIS ]
   (Network, DNS, TLS)                  (Semgrep SAST)
            │                                   │
            └─────────────────┬─────────────────┘
                              ▼
                   [ DEPENDENCY_ANALYSIS ]
                    (Lockfiles, SCA, CVE)
                              │
                              ▼
                  [ FINDING_NORMALIZATION ]
                     (Deduplication, AST)
                              │
                              ▼
                       [ AI_ANALYSIS ]
                  (Multi-Agent Verification)
                              │
                              ▼
                      [ RISK_ANALYSIS ]
                   (Deterministic Scoring)
                              │
                              ▼
                 [ ATTACK_PATH_CORRELATION ]
                   (Graph-Based Attack Map)
                              │
                              ▼
                       [ SCAN_COMPLETED ]
```

---

## 2. Phase-by-Phase Execution Flow

### Phase 1: `SCAN_REQUESTED` & `AUTHORIZATION_CHECK`
- **Trigger**: User initiates scan via UI or scheduled cron trigger.
- **Backend Gate**: Queries `asset_authorizations` for the target `asset_id`.
  - Condition: `status == 'verified' AND (expires_at IS NULL OR expires_at > now())`.
  - If condition fails: Scan is rejected immediately with error `E_TARGET_UNAUTHORIZED`. No network traffic or worker job is generated.

### Phase 2: `ASSET_VALIDATION`
- Target URL/URI is inspected against anti-SSRF filters, private IP ranges, and syntax validators.
- Target reachability check confirms repo availability or host response.

### Phase 3: `SCAN_CREATED`
- Scan record created in database with `status = 'queued'`. Initial scan events logged.

### Phase 4: `RECON` (Surface Discovery)
- Executed by the worker runner for application/infra targets.
- Probes TLS configurations, security headers (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`), exposed endpoints, and DNS metadata.
- Outputs raw telemetry to Supabase Storage.

### Phase 5: `CODE_ANALYSIS` (Semgrep SAST)
- Clones target repository to an isolated, ephemeral sandbox directory.
- Detects project languages (Python, JavaScript/TypeScript, Go, Java, Rust).
- Executes Semgrep with curated security rule packs (OWASP, CWE Top 25).
- Captures structured SARIF / JSON output.

### Phase 6: `DEPENDENCY_ANALYSIS` (SCA)
- Ingests lockfiles (`package-lock.json`, `poetry.lock`, `requirements.txt`, `go.sum`).
- Identifies vulnerable package versions against National Vulnerability Database (NVD) and GitHub Advisory Database.

### Phase 7: `FINDING_NORMALIZATION`
- Ingests raw outputs from Recon, Semgrep, and Dependency analyzers.
- Computes SHA-256 fingerprint (`hash(asset_id + rule_id + file_path + line)`) to deduplicate recurring findings.
- Normalizes disparate schemas into standard `Finding` database records.

### Phase 8: `AI_ANALYSIS`
- The AI Security Manager activates the Code Security Agent, Recon Agent, and Dependency Agent.
- Agents verify true positives, eliminate false alarms, extract root cause explanations, and attach evidence records.

### Phase 9: `RISK_ANALYSIS`
- Feeds normalized findings and AI assessments into the deterministic risk engine.
- Calculates mathematical risk scores (0.0 to 100.0) based on severity, exploitability, exposure, and asset criticality.

### Phase 10: `ATTACK_PATH_CORRELATION`
- The Threat Analyst Agent links isolated findings into reachable attack paths (e.g., Public API $\longrightarrow$ Unauthenticated Endpoint $\longrightarrow$ SQLi $\longrightarrow$ Database Crown Jewel).
- Persists nodes and edges into `attack_paths`, `attack_path_nodes`, and `attack_path_edges`.

### Phase 11: `SCAN_COMPLETED`
- Summarizes finding counts, updates scan duration and completion timestamps, recalibrates workspace aggregate security score, and dispatches completion webhooks to n8n.

---

## 3. Failure, Timeout & Cancellation States

The scan pipeline handles disruptions cleanly:

| State | Trigger Cause | Transition Action | UI / Cleanup Behavior |
|---|---|---|---|
| **`failed`** | Syntax crash, git clone failure, Semgrep error, unhandled exception | Record `error_message` in `scans` table, log error event in `scan_events` | Alerts user, frees worker sandbox, updates UI badge to red error state |
| **`cancelled`** | User explicitly clicks "Cancel Scan" | Sends `SIGTERM` / cancellation token to running worker subprocess | Wipes sandbox, updates status to `cancelled`, preserves partial findings |
| **`timed_out`** | Scan execution exceeds maximum timeout (default 30 mins) | Worker watchdog issues hard kill to Semgrep and agent processes | Marks scan `failed` (`E_TIMEOUT`), stores partial telemetry |
| **`aborted`** | Pre-flight authorization check fails | Aborts before worker allocation | Returns HTTP 403, logs audit event, no scan record created |

---

## 4. Worker Sandbox & Isolation Rules

- **Ephemeral Storage**: All cloned repositories reside in temporary in-memory or `/tmp` directories mounted with `noexec` options where possible.
- **Resource Limits**: Every Semgrep and worker process is constrained with cgroups:
  - Max Memory: 2GB per worker.
  - Max CPU: 2 vCPUs per worker.
  - Timeout: 600 seconds per SAST execution.
- **Immediate Scrubbing**: On scan termination (`completed`, `failed`, or `cancelled`), temporary directories are securely wiped (`rm -rf`) to prevent disk exhaustion and data retention on the host.
