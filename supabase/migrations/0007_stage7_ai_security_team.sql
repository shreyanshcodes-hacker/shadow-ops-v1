-- ==============================================================================
-- SHADOWOPS STAGE 7: AI SECURITY TEAM & MULTI-AGENT ORCHESTRATION
-- ==============================================================================
-- Migration: 0007_stage7_ai_security_team.sql
-- Creates security_team_runs and extends agent_runs for multi-agent orchestration.

-- 1. Create security_team_runs table
CREATE TABLE IF NOT EXISTS security_team_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (
        status IN ('QUEUED', 'RUNNING', 'PARTIAL', 'SUCCEEDED', 'FAILED', 'CANCELED')
    ),
    requested_by UUID NOT NULL REFERENCES profiles(id) ON DELETE RESTRICT,
    orchestration_version TEXT NOT NULL DEFAULT 'security-team-v1',
    team_summary JSONB DEFAULT '{}'::jsonb NOT NULL,
    confidence DECIMAL(3,2) NOT NULL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_team_runs_ws_id ON security_team_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_team_runs_asset_id ON security_team_runs(asset_id);
CREATE INDEX IF NOT EXISTS idx_team_runs_scan_id ON security_team_runs(scan_id);
CREATE INDEX IF NOT EXISTS idx_team_runs_status ON security_team_runs(status);
CREATE INDEX IF NOT EXISTS idx_team_runs_created ON security_team_runs(created_at DESC);

-- 2. Extend agent_runs table for team orchestration
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS team_run_id UUID REFERENCES security_team_runs(id) ON DELETE CASCADE;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS input_reference JSONB DEFAULT '{}'::jsonb;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS output JSONB DEFAULT '{}'::jsonb;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2) DEFAULT 0.0;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS attempt INT DEFAULT 1 NOT NULL;
ALTER TABLE agent_runs ALTER COLUMN scan_id DROP NOT NULL;

-- Update status check constraint on agent_runs to support agent contract statuses
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_agent_status'
    ) THEN
        ALTER TABLE agent_runs DROP CONSTRAINT check_agent_status;
        ALTER TABLE agent_runs ADD CONSTRAINT check_agent_status
            CHECK (status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'BLOCKED', 'pending', 'running', 'completed', 'failed', 'timeout'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_agent_runs_team_run ON agent_runs(team_run_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_team_agent ON agent_runs(team_run_id, agent_name);

-- 3. Row Level Security for security_team_runs
ALTER TABLE security_team_runs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE policyname = 'security_team_runs_workspace_isolation' 
        AND tablename = 'security_team_runs'
    ) THEN
        CREATE POLICY security_team_runs_workspace_isolation ON security_team_runs
            FOR ALL
            USING (workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()));
    END IF;
END $$;
