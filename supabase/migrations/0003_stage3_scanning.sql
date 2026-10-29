-- ==============================================================================
-- SHADOWOPS STAGE 3: CONTROLLED SCANNING & SCAN EVENTS EXTENSION
-- ==============================================================================
-- Migration: 0003_stage3_scanning.sql
-- Integrates with existing 001_initial_schema.sql while aligning scans and scan_events
-- with Stage 3 controlled execution requirements.

-- Ensure scan profiles and statuses are documented and supported
COMMENT ON TABLE scans IS 'Stores controlled execution records for authorized security scans.';
COMMENT ON TABLE scan_events IS 'Immutable chronological timeline of state transitions and tool outputs.';

-- Performance Indexes for Scan Operations
CREATE INDEX IF NOT EXISTS idx_scans_workspace_status ON scans(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_scans_asset_created ON scans(asset_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scan_events_scan_created ON scan_events(scan_id, created_at ASC);

-- Add explicit RLS policies if not already present
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_events ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'scans' AND policyname = 'workspace_isolation_scans'
    ) THEN
        CREATE POLICY workspace_isolation_scans ON scans
            FOR ALL
            USING (
                EXISTS (
                    SELECT 1 FROM workspace_members
                    WHERE workspace_members.workspace_id = scans.workspace_id
                    AND workspace_members.user_id = auth.uid()
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'scan_events' AND policyname = 'workspace_isolation_scan_events'
    ) THEN
        CREATE POLICY workspace_isolation_scan_events ON scan_events
            FOR ALL
            USING (
                EXISTS (
                    SELECT 1 FROM workspace_members
                    WHERE workspace_members.workspace_id = scan_events.workspace_id
                    AND workspace_members.user_id = auth.uid()
                )
            );
    END IF;
END $$;
