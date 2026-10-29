-- ==============================================================================
-- SHADOWOPS STAGE 6: ATTACK PATH INTELLIGENCE & DETERMINISTIC RISK ENGINE
-- ==============================================================================
-- Migration: 0006_stage6_attack_paths.sql
-- Creates security_relationships and risk_snapshots tables, and extends attack_paths.

-- 1. Create security_relationships table
CREATE TABLE IF NOT EXISTS security_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source_finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    target_finding_id UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL CHECK (
        relationship_type IN (
            'DEPENDS_ON',
            'ENABLES',
            'EXPOSES',
            'LEADS_TO',
            'SHARES_COMPONENT',
            'SHARES_ENTRY_POINT',
            'SHARES_DATA_FLOW',
            'AMPLIFIES'
        )
    ),
    confidence DECIMAL(3,2) NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source TEXT NOT NULL CHECK (source IN ('DETERMINISTIC', 'AI_SUGGESTED', 'HUMAN_CONFIRMED')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'confirmed', 'dismissed')),
    rationale TEXT,
    evidence_reference JSONB DEFAULT '{}'::jsonb NOT NULL,
    confirmed_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT chk_diff_findings CHECK (source_finding_id <> target_finding_id)
);

CREATE INDEX IF NOT EXISTS idx_sec_rel_ws_id ON security_relationships(workspace_id);
CREATE INDEX IF NOT EXISTS idx_sec_rel_source ON security_relationships(source_finding_id);
CREATE INDEX IF NOT EXISTS idx_sec_rel_target ON security_relationships(target_finding_id);
CREATE INDEX IF NOT EXISTS idx_sec_rel_type ON security_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_sec_rel_status ON security_relationships(status);
CREATE INDEX IF NOT EXISTS idx_sec_rel_source_type ON security_relationships(source);

-- 2. Extend attack_paths table
ALTER TABLE attack_paths ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE attack_paths ADD COLUMN IF NOT EXISTS risk_band TEXT CHECK (
    risk_band IS NULL OR risk_band IN ('INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
);
ALTER TABLE attack_paths ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2) DEFAULT 1.0;
ALTER TABLE attack_paths ADD COLUMN IF NOT EXISTS factors JSONB DEFAULT '{}'::jsonb;
ALTER TABLE attack_paths ADD COLUMN IF NOT EXISTS model_version TEXT DEFAULT 'risk-v1';

-- Update check constraint on attack_paths status to support broader lifecycle states
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'check_attack_path_status'
    ) THEN
        ALTER TABLE attack_paths DROP CONSTRAINT check_attack_path_status;
        ALTER TABLE attack_paths ADD CONSTRAINT check_attack_path_status
            CHECK (status IN ('active', 'mitigated', 'broken', 'draft', 'resolved', 'dismissed'));
    END IF;
END $$;

-- 3. Create risk_snapshots table
CREATE TABLE IF NOT EXISTS risk_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    attack_path_id UUID REFERENCES attack_paths(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
    score DECIMAL(5,2) NOT NULL CHECK (score >= 0.0 AND score <= 100.0),
    risk_band TEXT NOT NULL CHECK (risk_band IN ('INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    model_version TEXT NOT NULL DEFAULT 'risk-v1',
    factors JSONB NOT NULL DEFAULT '{}'::jsonb,
    calculated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    calculated_by TEXT NOT NULL DEFAULT 'deterministic_engine'
);

CREATE INDEX IF NOT EXISTS idx_risk_snap_ws_id ON risk_snapshots(workspace_id);
CREATE INDEX IF NOT EXISTS idx_risk_snap_path_id ON risk_snapshots(attack_path_id);
CREATE INDEX IF NOT EXISTS idx_risk_snap_finding_id ON risk_snapshots(finding_id);
CREATE INDEX IF NOT EXISTS idx_risk_snap_calculated ON risk_snapshots(calculated_at DESC);

-- 4. Enable RLS and add workspace isolation policies
ALTER TABLE security_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_snapshots ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'security_relationships_workspace_isolation' AND tablename = 'security_relationships') THEN
        CREATE POLICY security_relationships_workspace_isolation ON security_relationships
            FOR ALL
            USING (workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()));
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'risk_snapshots_workspace_isolation' AND tablename = 'risk_snapshots') THEN
        CREATE POLICY risk_snapshots_workspace_isolation ON risk_snapshots
            FOR ALL
            USING (workspace_id IN (SELECT workspace_id FROM workspace_members WHERE user_id = auth.uid()));
    END IF;
END $$;
