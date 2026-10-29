-- ============================================================
-- Stage 10: Security Reports & Executive Dashboard
-- ============================================================

-- Add new columns to reports table
ALTER TABLE reports ADD COLUMN IF NOT EXISTS snapshot_data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS parameters JSONB DEFAULT '{}'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS data_cutoff_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE reports ADD COLUMN IF NOT EXISTS schema_version TEXT DEFAULT 'report-v1';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS completeness_status TEXT DEFAULT 'COMPLETE';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS error_message TEXT;

-- Drop old check constraints if needed and replace with expanded constraints
ALTER TABLE reports DROP CONSTRAINT IF EXISTS check_report_type;
ALTER TABLE reports ADD CONSTRAINT check_report_type CHECK (
    report_type IN (
        'executive_summary', 'technical_vulnerability', 
        'remediation_progress', 'verification_regression', 
        'asset_security_posture', 'executive', 'technical', 
        'scan', 'compliance', 'custom'
    )
);

ALTER TABLE reports DROP CONSTRAINT IF EXISTS check_report_status;
ALTER TABLE reports ADD CONSTRAINT check_report_status CHECK (
    status IN ('generating', 'completed', 'ready', 'failed')
);

CREATE INDEX IF NOT EXISTS idx_reports_cutoff ON reports(data_cutoff_at);
CREATE INDEX IF NOT EXISTS idx_reports_schema ON reports(schema_version);
