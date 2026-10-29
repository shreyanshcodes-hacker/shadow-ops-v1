-- ==============================================================================
-- SHADOWOPS STAGE 4: AI SECURITY MANAGER & STRUCTURED SECURITY ANALYSIS
-- ==============================================================================
-- Migration: 0004_stage4_ai.sql
-- Integrates with existing 001_initial_schema.sql and 0003_stage3_scanning.sql.
-- Provides storage for structured, evidence-grounded AI findings analysis,
-- and extends agent_runs for execution tracking, token usage, and cost controls.

-- 1. Extend agent_runs with execution tracking fields if not present
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS provider TEXT;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS prompt_version TEXT;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS input_hash TEXT;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS error_code TEXT;

-- 2. Create finding_ai_analysis table
CREATE TABLE IF NOT EXISTS finding_ai_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    ai_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    technical_explanation TEXT NOT NULL,
    impact TEXT NOT NULL,
    confidence NUMERIC(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    classification TEXT NOT NULL,
    uncertainty TEXT,
    supporting_evidence JSONB DEFAULT '[]'::jsonb NOT NULL,
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. Performance Indexes
CREATE INDEX IF NOT EXISTS idx_finding_ai_analysis_finding_id ON finding_ai_analysis(finding_id);
CREATE INDEX IF NOT EXISTS idx_finding_ai_analysis_workspace_id ON finding_ai_analysis(workspace_id);
CREATE INDEX IF NOT EXISTS idx_finding_ai_analysis_ai_run_id ON finding_ai_analysis(ai_run_id);
CREATE INDEX IF NOT EXISTS idx_finding_ai_analysis_input_hash ON finding_ai_analysis(input_hash);
CREATE INDEX IF NOT EXISTS idx_agent_runs_input_hash ON agent_runs(input_hash);

-- 4. Enable Row Level Security (RLS)
ALTER TABLE finding_ai_analysis ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'finding_ai_analysis' AND policyname = 'workspace_isolation_finding_ai_analysis'
    ) THEN
        CREATE POLICY workspace_isolation_finding_ai_analysis ON finding_ai_analysis
            FOR ALL
            USING (
                EXISTS (
                    SELECT 1 FROM workspace_members
                    WHERE workspace_members.workspace_id = finding_ai_analysis.workspace_id
                    AND workspace_members.user_id = auth.uid()
                )
            );
    END IF;
END $$;
