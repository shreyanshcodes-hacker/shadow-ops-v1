-- ============================================================
-- Stage 9: Independent Fix Verification & Regression Analysis
-- ============================================================

CREATE TABLE IF NOT EXISTS verification_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    proposal_id UUID REFERENCES remediation_proposals(id) ON DELETE SET NULL,
    application_id UUID REFERENCES remediation_applications(id) ON DELETE SET NULL,
    rescan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (
        status IN (
            'QUEUED', 'RUNNING', 'BASELINE_CHECK', 'RESCANNING', 
            'REGRESSION_CHECK', 'COMPARING_EVIDENCE', 'PASSED_PENDING_REVIEW', 
            'FAILED', 'INCONCLUSIVE', 'BLOCKED', 'CANCELED'
        )
    ),
    vulnerability_status TEXT NOT NULL DEFAULT 'UNCOMPARABLE' CHECK (
        vulnerability_status IN (
            'STILL_PRESENT', 'NO_LONGER_DETECTED', 'MODIFIED_OR_MOVED', 
            'POSSIBLE_REGRESSION', 'NEW_FINDING', 'UNCOMPARABLE'
        )
    ),
    regression_status TEXT NOT NULL DEFAULT 'SKIPPED' CHECK (
        regression_status IN ('PASS', 'FAIL', 'SKIPPED', 'BLOCKED', 'ERROR')
    ),
    scanner_status TEXT NOT NULL DEFAULT 'COMPLETED' CHECK (
        scanner_status IN ('COMPLETED', 'FAILED', 'BLOCKED', 'TIMEOUT', 'SCANNER_UNAVAILABLE')
    ),
    test_status TEXT NOT NULL DEFAULT 'SKIPPED' CHECK (
        test_status IN ('PASS', 'FAIL', 'SKIPPED', 'BLOCKED', 'ERROR')
    ),
    policy_verdict TEXT NOT NULL DEFAULT 'INCONCLUSIVE' CHECK (
        policy_verdict IN ('VERIFIED_CANDIDATE', 'FAILED', 'INCONCLUSIVE', 'BLOCKED')
    ),
    policy_version TEXT NOT NULL DEFAULT 'verification-policy-v1',
    policy_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    baseline_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_revision TEXT,
    target_revision TEXT,
    patch_hash TEXT,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verif_jobs_workspace ON verification_jobs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_verif_jobs_finding ON verification_jobs(finding_id);
CREATE INDEX IF NOT EXISTS idx_verif_jobs_proposal ON verification_jobs(proposal_id);
CREATE INDEX IF NOT EXISTS idx_verif_jobs_status ON verification_jobs(status);
CREATE INDEX IF NOT EXISTS idx_verif_jobs_verdict ON verification_jobs(policy_verdict);

CREATE TABLE IF NOT EXISTS verification_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES verification_jobs(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    comparison_category TEXT NOT NULL CHECK (
        comparison_category IN (
            'STILL_PRESENT', 'NO_LONGER_DETECTED', 'MODIFIED_OR_MOVED', 
            'POSSIBLE_REGRESSION', 'NEW_FINDING', 'UNCOMPARABLE'
        )
    ),
    rule_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    baseline_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    rescan_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    line_shift INT NOT NULL DEFAULT 0,
    similarity_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verif_comp_job ON verification_comparisons(job_id);
CREATE INDEX IF NOT EXISTS idx_verif_comp_ws ON verification_comparisons(workspace_id);
CREATE INDEX IF NOT EXISTS idx_verif_comp_cat ON verification_comparisons(comparison_category);

CREATE TABLE IF NOT EXISTS verification_regression_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES verification_jobs(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'SKIPPED', 'BLOCKED', 'ERROR')),
    duration_ms INT NOT NULL DEFAULT 0,
    output_summary TEXT NOT NULL DEFAULT '',
    error_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verif_reg_job ON verification_regression_checks(job_id);
CREATE INDEX IF NOT EXISTS idx_verif_reg_ws ON verification_regression_checks(workspace_id);

CREATE TABLE IF NOT EXISTS verification_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES verification_jobs(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected')),
    rationale TEXT NOT NULL,
    finding_status_after TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verif_rev_job ON verification_reviews(job_id);
CREATE INDEX IF NOT EXISTS idx_verif_rev_ws ON verification_reviews(workspace_id);
CREATE INDEX IF NOT EXISTS idx_verif_rev_finding ON verification_reviews(finding_id);

-- Enable Row Level Security (RLS)
ALTER TABLE verification_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_regression_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_reviews ENABLE ROW LEVEL SECURITY;
