-- ==============================================================================
-- SHADOWOPS STAGE 8: AI REMEDIATION, HUMAN APPROVAL & SAFE PATCH MANAGEMENT
-- ==============================================================================
-- Migration: 0008_stage8_remediation.sql

-- 1. Extend remediation_proposals table with Stage 8 capabilities
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS asset_id UUID REFERENCES assets(id) ON DELETE CASCADE;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS source_scan_id UUID REFERENCES scans(id) ON DELETE SET NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS proposal_title TEXT;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS problem_summary TEXT;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS proposed_solution TEXT;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS rationale TEXT;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS affected_files JSONB DEFAULT '[]'::jsonb NOT NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS patch_reference TEXT;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS unified_diff TEXT DEFAULT '' NOT NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS patch_hash TEXT DEFAULT '' NOT NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS validation_results JSONB DEFAULT '{}'::jsonb NOT NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES profiles(id) ON DELETE SET NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES profiles(id) ON DELETE SET NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS applied_by UUID REFERENCES profiles(id) ON DELETE SET NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS failure_reason TEXT;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS version INT DEFAULT 1 NOT NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS target_base_revision TEXT;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS risk_assessment JSONB DEFAULT '{}'::jsonb NOT NULL;
ALTER TABLE remediation_proposals ADD COLUMN IF NOT EXISTS suggested_tests JSONB DEFAULT '[]'::jsonb NOT NULL;

-- Drop old check constraint on status if exists and update with Stage 8 state machine
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_proposal_status'
    ) THEN
        ALTER TABLE remediation_proposals DROP CONSTRAINT check_proposal_status;
        ALTER TABLE remediation_proposals ADD CONSTRAINT check_proposal_status CHECK (
            status IN (
                'DRAFT', 'GENERATING', 'PROPOSED', 'VALIDATING', 'VALIDATION_FAILED',
                'AWAITING_APPROVAL', 'APPROVED', 'APPLYING', 'APPLIED', 'REJECTED',
                'EXPIRED', 'ROLLED_BACK', 'FAILED',
                'proposed', 'approved', 'rejected', 'applied', 'superseded'
            )
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_remediation_proposals_asset_id ON remediation_proposals(asset_id);
CREATE INDEX IF NOT EXISTS idx_remediation_proposals_scan_id ON remediation_proposals(source_scan_id);
CREATE INDEX IF NOT EXISTS idx_remediation_proposals_patch_hash ON remediation_proposals(patch_hash);

-- 2. Extend remediation_approvals table
ALTER TABLE remediation_approvals ADD COLUMN IF NOT EXISTS patch_hash TEXT DEFAULT '' NOT NULL;
ALTER TABLE remediation_approvals ADD COLUMN IF NOT EXISTS proposal_version INT DEFAULT 1 NOT NULL;
ALTER TABLE remediation_approvals ADD COLUMN IF NOT EXISTS validation_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL;

-- 3. Create remediation_validations table
CREATE TABLE IF NOT EXISTS remediation_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'BLOCKED', 'SKIPPED')),
    duration_ms INT DEFAULT 0 NOT NULL,
    output_summary TEXT NOT NULL DEFAULT '',
    error_details TEXT,
    executed_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_remediation_val_proposal ON remediation_validations(proposal_id);
CREATE INDEX IF NOT EXISTS idx_remediation_val_workspace ON remediation_validations(workspace_id);

-- 4. Create remediation_checkpoints table
CREATE TABLE IF NOT EXISTS remediation_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    checkpoint_type TEXT NOT NULL DEFAULT 'file_snapshot' CHECK (checkpoint_type IN ('git_commit', 'file_snapshot', 'worktree')),
    base_revision TEXT NOT NULL DEFAULT 'HEAD',
    snapshot_data JSONB DEFAULT '{}'::jsonb NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_remediation_chk_proposal ON remediation_checkpoints(proposal_id);
CREATE INDEX IF NOT EXISTS idx_remediation_chk_workspace ON remediation_checkpoints(workspace_id);

-- 5. Create remediation_applications table
CREATE TABLE IF NOT EXISTS remediation_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES remediation_proposals(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    applied_by UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    checkpoint_id UUID REFERENCES remediation_checkpoints(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'APPLIED' CHECK (status IN ('APPLYING', 'APPLIED', 'FAILED', 'ROLLED_BACK')),
    patch_hash TEXT NOT NULL,
    applied_diff TEXT NOT NULL,
    changed_files JSONB DEFAULT '[]'::jsonb NOT NULL,
    target_revision TEXT,
    verification_status TEXT DEFAULT 'VERIFICATION_PENDING' NOT NULL CHECK (
        verification_status IN ('VERIFICATION_PENDING', 'VERIFYING', 'VERIFIED', 'FAILED')
    ),
    applied_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    rolled_back_at TIMESTAMPTZ,
    rolled_back_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_remediation_app_proposal ON remediation_applications(proposal_id);
CREATE INDEX IF NOT EXISTS idx_remediation_app_workspace ON remediation_applications(workspace_id);
CREATE INDEX IF NOT EXISTS idx_remediation_app_status ON remediation_applications(status);

-- Enable RLS on new tables
ALTER TABLE remediation_validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE remediation_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE remediation_applications ENABLE ROW LEVEL SECURITY;
