-- ==============================================================================
-- SHADOWOPS STAGE 5: AI SECURITY ANALYST EXTENSION
-- ==============================================================================
-- Migration: 0005_stage5_ai_analyst.sql
-- Extends finding_ai_analysis to support full structured SecurityAnalysis schemas,
-- historical analysis versioning (multiple analyses per finding), and detailed
-- execution tracking.

-- 1. Add status and execution tracking columns to finding_ai_analysis
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'SUCCEEDED' NOT NULL;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS vulnerability_type TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS severity_assessment TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS exploitability_assessment TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS impact_assessment TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS affected_component TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS attack_preconditions TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS evidence_interpretation JSONB DEFAULT '{}'::jsonb;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS reasoning TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS recommended_next_steps TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS raw_analysis JSONB DEFAULT '{}'::jsonb;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES profiles(id) ON DELETE SET NULL;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS error_code TEXT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS tokens_input INT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS tokens_output INT;
ALTER TABLE finding_ai_analysis ADD COLUMN IF NOT EXISTS cost_usd NUMERIC(10, 6);

-- 2. Drop unique constraint on finding_id if present to allow multiple historical analyses
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'finding_ai_analysis_finding_id_key'
    ) THEN
        ALTER TABLE finding_ai_analysis DROP CONSTRAINT finding_ai_analysis_finding_id_key;
    END IF;
END $$;

-- 3. Composite performance index for historical analysis lookups
CREATE INDEX IF NOT EXISTS idx_finding_ai_analysis_finding_created ON finding_ai_analysis(finding_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_finding_ai_analysis_status ON finding_ai_analysis(status);
