# ShadowOps — Phase 13A Staging Infrastructure Cost Recalculation

**Document Version:** 1.0  
**Date:** October 30, 2026  
**Target Environment:** Staging  
**Primary Region:** `us-central1` (Iowa, USA)  
**Currency:** USD ($)  

---

## 1. Cost Model Overview

The staging environment is deliberately sized to validate full PostgreSQL 16 functionality, Private Service Access (VPC Peering), Serverless VPC Access for Cloud Run, and Firebase Data Connect without incurring production-scale high availability or multi-region redundancy costs.

### Summary Cost Table:

| Subsystem | Specific SKU / Sizing | Monthly Cost (Continuous) | Daily Run Rate |
| :--- | :--- | :--- | :--- |
| **Cloud SQL Compute** | `db-custom-1-3840` (1 vCPU, 3.75 GB RAM) | $49.31 | ~$1.64 / day |
| **Cloud SQL Storage** | 20 GB SSD (`pd-ssd`) | $3.40 | ~$0.11 / day |
| **Cloud SQL Backups** | 7 days retention + WAL logs (~5 GB) | $0.40 | ~$0.01 / day |
| **Serverless VPC Access** | 2 `f1-micro` / `e2-micro` instances | $10.51 | ~$0.35 / day |
| **Cloud Run Backend** | Scale to 0 (Min: 0, Max: 3) | $0.00 – $1.50 | ~$0.00 – $0.05 / day |
| **Artifact Registry** | Docker image storage (~1.5 GB) | $0.15 | <$0.01 / day |
| **Cloud Storage** | Standard regional bucket (< 5 GB) | $0.10 | <$0.01 / day |
| **Secret Manager** | 3 active secrets (< 10k calls) | $0.18 | <$0.01 / day |
| **Firebase Data Connect**| Staging / Developer quota | $0.00 | $0.00 |
| **TOTAL ESTIMATED COST**| | **~$64.05 – $65.55 / month** | **~$2.12 – $2.18 / day** |

---

## 2. Itemized Breakdown & Mathematical Basis

### 2.1 Cloud SQL for PostgreSQL 16 (`shadowops-staging-pg`)
- **vCPU Rate (`us-central1`):** $0.0413 per vCPU-hour.
  $$1 \text{ vCPU} \times \$0.0413 \times 730 \text{ hours} = \$30.15$$
- **RAM Rate (`us-central1`):** $0.0070 per GB-hour.
  $$3.75 \text{ GB} \times \$0.0070 \times 730 \text{ hours} = \$19.16$$
- **Compute Subtotal:** $\$30.15 + \$19.16 = \$49.31 \text{ / month}$
- **SSD Storage (`pd-ssd`):** $0.170 per GB-month.
  $$20 \text{ GB} \times \$0.170 = \$3.40 \text{ / month}$$
- **Backup Storage:** $0.080 per GB-month.
  $$5 \text{ GB} \times \$0.080 = \$0.40 \text{ / month}$$
- **Total Cloud SQL:** **$53.11 / month** (~$0.073 / hour)

### 2.2 Serverless VPC Access Connector (`staging-vpc-conn`)
- Serverless VPC Access connectors require a minimum of 2 instances to maintain high availability and prevent packet dropping during scaling.
- **Instance Type:** `e2-micro` / `f1-micro` at ~$0.0072 per instance-hour.
  $$2 \text{ instances} \times \$0.0072 \times 730 \text{ hours} = \$10.51 \text{ / month}$$

### 2.3 Cloud Run (`shadowops-staging-api`)
- Google Cloud Run offers a generous free tier every month:
  - First 2,000,000 requests are free.
  - First 360,000 vCPU-seconds are free.
  - First 180,000 GiB-seconds are free.
- **Min-Instances: 0:** The staging backend scales down to 0 instances when idle, incurring $0 compute charges.
- **Estimated Test Suite Usage:** Running 10 full end-to-end integration test runs per week consumes ~15,000 vCPU-seconds and ~30,000 requests, well within the free tier.
- **Budgeted Cost:** **$0.00 – $1.50 / month**.

### 2.4 Artifact Registry & Storage
- Artifact Registry charges $0.10 per GB-month. Storing 1 base container image (~1.5 GB) = **$0.15 / month**.
- Cloud Storage regional bucket for security evidence: 5 GB = **$0.10 / month**.

### 2.5 Secret Manager
- Secret Manager charges $0.06 per active secret version per month.
- 3 secrets (`migrator-password`, `app-password`, `secret-key`) = **$0.18 / month**. Access operations (< 10,000 calls) are within the free tier.

---

## 3. Assumptions and Variable Charges

| Parameter | Underlying Assumption | Variable Risk & Mitigation |
| :--- | :--- | :--- |
| **Egress Bandwidth** | All database calls traverse Private Service Access within `us-central1`. | Cross-region egress charges are $0.00 as long as Cloud Run and Cloud SQL remain in the same region. |
| **Storage Growth** | `--storage-auto-increase` is enabled. | If synthetic tests generate massive payloads, storage expands in 5 GB increments ($0.85/month per 5 GB). |
| **Idle vs. Active** | Staging is used during working/testing hours. | If Cloud SQL is shut down or destroyed after verification testing, the total cost for 48 hours of testing is **less than $5.00**. |
