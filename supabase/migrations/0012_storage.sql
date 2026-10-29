-- ==============================================================================
-- SHADOWOPS SUPABASE STORAGE SPECIFICATION — STORAGE.SQL
-- Storage Buckets & Access Control Policies for Security Artifacts
-- ==============================================================================

-- Create designated storage buckets (all private by default)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
  ('scan-artifacts', 'scan-artifacts', false, 104857600, ARRAY['application/json', 'application/sarif+json', 'text/plain', 'application/zip']),
  ('evidence-files', 'evidence-files', false, 52428800, ARRAY['image/png', 'image/jpeg', 'image/webp', 'text/plain', 'application/json', 'application/pdf']),
  ('security-reports', 'security-reports', false, 104857600, ARRAY['application/pdf', 'text/html', 'application/json', 'text/markdown']),
  ('remediation-artifacts', 'remediation-artifacts', false, 20971520, ARRAY['text/plain', 'text/x-diff', 'text/x-patch', 'application/json']),
  ('verification-artifacts', 'verification-artifacts', false, 52428800, ARRAY['text/plain', 'application/json', 'image/png', 'image/jpeg'])
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Helper function: extract workspace UUID from object path convention (e.g. "workspace_id/...")
CREATE OR REPLACE FUNCTION storage_object_workspace_id(name TEXT)
RETURNS UUID LANGUAGE sql IMMUTABLE AS $$
  SELECT (string_to_array(name, '/'))[1]::uuid;
$$;

-- Universal Storage Read Policy: Only active members of the workspace can read objects
CREATE POLICY "workspace_members_read_storage" ON storage.objects
  FOR SELECT USING (
    bucket_id IN ('scan-artifacts', 'evidence-files', 'security-reports', 'remediation-artifacts', 'verification-artifacts') AND
    EXISTS (
      SELECT 1 FROM public.workspace_members
      WHERE workspace_id = (string_to_array(name, '/'))[1]::uuid
      AND user_id = auth.uid()
      AND joined_at IS NOT NULL
    )
  );

-- Backend Service Role / Admin Write Policy
CREATE POLICY "service_role_and_admins_insert_storage" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id IN ('scan-artifacts', 'evidence-files', 'security-reports', 'remediation-artifacts', 'verification-artifacts') AND
    (
      auth.role() = 'service_role' OR
      EXISTS (
        SELECT 1 FROM public.workspace_members
        WHERE workspace_id = (string_to_array(name, '/'))[1]::uuid
        AND user_id = auth.uid()
        AND role IN ('owner', 'admin')
        AND joined_at IS NOT NULL
      )
    )
  );
