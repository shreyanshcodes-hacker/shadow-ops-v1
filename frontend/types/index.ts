export interface Profile {
  id: string;
  firebase_uid: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  created_at: string;
  updated_at: string;
}

export type WorkspaceRole = "owner" | "admin" | "security_lead" | "engineer" | "viewer";

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  role: WorkspaceRole;
  email: string;
  display_name: string | null;
  invited_by: string | null;
  invited_at: string | null;
  joined_at: string;
}

export type AssetType = "repository" | "api" | "infrastructure" | "application" | "container";
export type AssetCriticality = "low" | "medium" | "high" | "critical";
export type AuthorizationStatus = "authorized" | "pending" | "revoked" | "expired" | "verified";

export interface Asset {
  id: string;
  workspace_id: string;
  name: string;
  type: AssetType;
  subtype: string | null;
  identifier: string | null;
  environment: string;
  criticality: AssetCriticality;
  description: string | null;
  connection_config: Record<string, unknown>;
  tags: string[];
  status: string;
  last_scanned_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  authorization_status: AuthorizationStatus | "pending";
}

export interface AssetAuthorization {
  id: string;
  asset_id: string;
  workspace_id: string;
  authorization_type: string;
  authorization_status: AuthorizationStatus;
  authorized_by: string | null;
  authorization_scope: string;
  authorization_reference: string | null;
  authorized_at: string | null;
  expires_at: string | null;
  status: AuthorizationStatus;
  verified_by: string | null;
  verified_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type ScanStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export type ScanProfile = "CODE_SECURITY" | "STANDARD" | "QUICK";

export interface ScanSummary {
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface Scan {
  id: string;
  workspace_id: string;
  asset_id: string;
  scan_type: string;
  scan_profile: string;
  status: ScanStatus;
  triggered_by: string;
  triggered_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  progress_percent: number;
  error_message: string | null;
  summary: ScanSummary;
  created_at: string;
  updated_at: string;
}

export interface ScanEvent {
  id: number;
  scan_id: string;
  workspace_id: string;
  event_type: string;
  message: string;
  data: Record<string, unknown>;
  created_at: string;
}

export interface Finding {
  id: string;
  workspace_id: string;
  scan_id: string;
  asset_id: string;
  source: string;
  source_rule_id: string | null;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  confidence: string;
  cwe_ids: string[];
  owasp_categories: string[];
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  code_snippet: string | null;
  status: string;
  created_at: string;
}

export interface SupportingEvidenceItem {
  evidence_id: string;
  relevance: string;
  quote_or_reference?: string;
}

export interface EvidenceInterpretation {
  observed: string[];
  inferred: string[];
  uncertain: string[];
}

export interface FindingAIAnalysis {
  id: string;
  finding_id: string;
  ai_run_id?: string;
  workspace_id: string;
  status: string;
  summary: string;
  technical_explanation: string;
  impact: string;
  confidence: number;
  classification: string;
  uncertainty?: string;
  vulnerability_type?: string;
  severity_assessment?: string;
  exploitability_assessment?: string;
  impact_assessment?: string;
  affected_component?: string;
  attack_preconditions?: string;
  evidence_interpretation?: EvidenceInterpretation;
  reasoning?: string;
  recommended_next_steps?: string;
  raw_analysis?: Record<string, unknown>;
  supporting_evidence: SupportingEvidenceItem[];
  model: string;
  provider: string;
  prompt_version: string;
  input_hash?: string;
  created_by?: string;
  completed_at?: string;
  error_code?: string;
  tokens_input?: number;
  tokens_output?: number;
  cost_usd?: number;
  created_at: string;
  updated_at: string;
}

export interface AIRun {
  id: string;
  scan_id: string;
  workspace_id: string;
  agent_name: string;
  provider?: string;
  model_used?: string;
  prompt_version?: string;
  status: "pending" | "running" | "completed" | "failed" | "timeout";
  input_summary?: Record<string, unknown>;
  output_summary?: Record<string, unknown>;
  tokens_input?: number;
  tokens_output?: number;
  cost_usd?: number;
  error_code?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ScanAnalysisSummaryResponse {
  scan_id: string;
  ai_run_id: string;
  status: string;
  findings_analyzed: number;
  findings_skipped_cached: number;
  total_findings: number;
  analyses: FindingAIAnalysis[];
}

export type RelationshipType =
  | "DEPENDS_ON"
  | "ENABLES"
  | "EXPOSES"
  | "LEADS_TO"
  | "SHARES_COMPONENT"
  | "SHARES_ENTRY_POINT"
  | "SHARES_DATA_FLOW"
  | "AMPLIFIES";

export type RelationshipSource = "DETERMINISTIC" | "AI_SUGGESTED" | "HUMAN_CONFIRMED";
export type RelationshipStatus = "active" | "confirmed" | "dismissed";
export type RiskBand = "INFORMATIONAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface SecurityRelationship {
  id: string;
  workspace_id: string;
  source_finding_id: string;
  target_finding_id: string;
  relationship_type: RelationshipType;
  confidence: number;
  source: RelationshipSource;
  status: RelationshipStatus;
  rationale?: string | null;
  evidence_reference?: Record<string, unknown>;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  created_at: string;
  updated_at: string;
  source_finding_title?: string | null;
  target_finding_title?: string | null;
}

export interface RiskFactorItem {
  score: number;
  weight: number;
  contribution: number;
  details?: string;
}

export interface RiskSnapshot {
  id: string;
  workspace_id: string;
  attack_path_id?: string | null;
  finding_id?: string | null;
  score: number;
  risk_band: RiskBand;
  model_version: string;
  factors: Record<string, RiskFactorItem>;
  calculated_at: string;
  calculated_by: string;
}

export interface AttackPathNode {
  id: string;
  attack_path_id: string;
  workspace_id: string;
  node_type: string;
  node_order: number;
  label: string;
  description?: string | null;
  asset_id?: string | null;
  finding_id?: string | null;
  risk_contribution: number;
  metadata_?: Record<string, unknown>;
  created_at: string;
  finding_title?: string | null;
  finding_severity?: string | null;
}

export interface AttackPathEdge {
  id: string;
  attack_path_id: string;
  workspace_id: string;
  source_node_id: string;
  target_node_id: string;
  edge_type: string;
  description?: string | null;
  evidence_refs: string[];
  likelihood?: number | null;
  created_at: string;
}

export interface AttackPath {
  id: string;
  workspace_id: string;
  scan_id?: string | null;
  name: string;
  title?: string | null;
  description?: string | null;
  entry_point?: string | null;
  target_asset?: string | null;
  risk_score?: number | null;
  risk_band?: RiskBand | null;
  confidence: number;
  node_count: number;
  edge_count: number;
  is_critical: boolean;
  status: string;
  factors?: Record<string, RiskFactorItem>;
  model_version: string;
  created_at: string;
  updated_at: string;
}

export interface AttackPathDetail extends AttackPath {
  nodes: AttackPathNode[];
  edges: AttackPathEdge[];
  risk_snapshots: RiskSnapshot[];
}

// Stage 7: AI Security Team & Orchestration Types
export type TeamRunStatus = "QUEUED" | "RUNNING" | "PARTIAL" | "SUCCEEDED" | "FAILED" | "CANCELED";
export type AgentStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "BLOCKED";

export interface TeamAgentRun {
  id: string;
  team_run_id?: string | null;
  agent_name: string;
  status: AgentStatus | string;
  provider?: string | null;
  model_used?: string | null;
  prompt_version?: string | null;
  confidence: number;
  attempt: number;
  input_reference: Record<string, unknown>;
  output: Record<string, unknown>;
  tokens_input?: number | null;
  tokens_output?: number | null;
  cost_usd?: number | null;
  error_code?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface TeamAssessment {
  review_status: string;
  executive_summary: string;
  key_security_concerns: string[];
  highest_priority_findings: string[];
  highest_priority_attack_paths: string[];
  risk_interpretation: string;
  uncertainties: string[];
  conflicting_assessments: string[];
  recommended_human_actions: string[];
  overall_confidence: number;
  evidence_references: string[];
}

export interface SecurityTeamRun {
  id: string;
  workspace_id: string;
  asset_id: string;
  scan_id?: string | null;
  status: TeamRunStatus;
  requested_by: string;
  orchestration_version: string;
  team_summary: Partial<TeamAssessment> & Record<string, unknown>;
  confidence: number;
  started_at?: string | null;
  completed_at?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SecurityTeamRunDetail extends SecurityTeamRun {
  agent_runs: TeamAgentRun[];
  assessment?: TeamAssessment | null;
}

// Stage 8: AI Remediation, Human Approval & Safe Patch Management
export type RemediationStatus =
  | "DRAFT"
  | "GENERATING"
  | "PROPOSED"
  | "VALIDATING"
  | "VALIDATION_FAILED"
  | "AWAITING_APPROVAL"
  | "APPROVED"
  | "APPLYING"
  | "APPLIED"
  | "REJECTED"
  | "EXPIRED"
  | "ROLLED_BACK"
  | "FAILED";

export type ValidationStatus = "PASS" | "FAIL" | "BLOCKED" | "SKIPPED";
export type ApplicationStatus = "APPLYING" | "APPLIED" | "FAILED" | "ROLLED_BACK";
export type VerificationStatus = "VERIFICATION_PENDING" | "VERIFYING" | "VERIFIED" | "FAILED";

export interface RemediationValidation {
  id: string;
  proposal_id: string;
  check_name: string;
  status: ValidationStatus;
  duration_ms: number;
  output_summary: string;
  error_details?: string | null;
  executed_at: string;
}

export interface RemediationApproval {
  id: string;
  proposal_id: string;
  approved_by: string;
  decision: "approved" | "rejected";
  patch_hash: string;
  proposal_version: number;
  justification?: string | null;
  validation_snapshot: Record<string, unknown>;
  approved_at: string;
}

export interface RemediationApplication {
  id: string;
  proposal_id: string;
  workspace_id: string;
  applied_by: string;
  checkpoint_id?: string | null;
  status: ApplicationStatus;
  patch_hash: string;
  applied_diff: string;
  changed_files: string[];
  target_revision?: string | null;
  verification_status: VerificationStatus;
  applied_at: string;
  rolled_back_at?: string | null;
  error_message?: string | null;
}

export interface RemediationProposal {
  id: string;
  workspace_id: string;
  asset_id?: string | null;
  finding_id: string;
  source_scan_id?: string | null;
  proposed_by: string;
  created_by?: string | null;
  model_used?: string | null;
  proposal_title: string;
  problem_summary: string;
  proposed_solution: string;
  rationale: string;
  affected_files: string[];
  unified_diff: string;
  patch_hash: string;
  risk_assessment: {
    compatibility_risks?: string[];
    assumptions?: string[];
    limitations?: string[];
  };
  suggested_tests: string[];
  target_base_revision?: string | null;
  validation_results: Record<string, unknown>;
  status: RemediationStatus;
  version: number;
  failure_reason?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  applied_by?: string | null;
  applied_at?: string | null;
  created_at: string;
  updated_at: string;
  validations?: RemediationValidation[];
  approvals?: RemediationApproval[];
  applications?: RemediationApplication[];
  finding?: Finding;
}

export interface RemediationListResponse {
  items: RemediationProposal[];
  total: number;
}

// ==============================================================================
// STAGE 9: VERIFICATION & REGRESSION ANALYSIS
// ==============================================================================
export type VerificationJobStatus =
  | "QUEUED"
  | "RUNNING"
  | "BASELINE_CHECK"
  | "RESCANNING"
  | "REGRESSION_CHECK"
  | "COMPARING_EVIDENCE"
  | "PASSED_PENDING_REVIEW"
  | "FAILED"
  | "INCONCLUSIVE"
  | "BLOCKED"
  | "CANCELED";

export type VulnerabilityVerificationStatus =
  | "STILL_PRESENT"
  | "NO_LONGER_DETECTED"
  | "MODIFIED_OR_MOVED"
  | "POSSIBLE_REGRESSION"
  | "NEW_FINDING"
  | "UNCOMPARABLE";

export type RegressionCheckStatus = "PASS" | "FAIL" | "SKIPPED" | "BLOCKED" | "ERROR";
export type ScannerVerificationStatus = "COMPLETED" | "FAILED" | "BLOCKED" | "TIMEOUT" | "SCANNER_UNAVAILABLE";
export type VerificationPolicyVerdict = "VERIFIED_CANDIDATE" | "FAILED" | "INCONCLUSIVE" | "BLOCKED";

export interface VerificationComparison {
  id: string;
  job_id: string;
  workspace_id: string;
  finding_id: string;
  comparison_category: VulnerabilityVerificationStatus;
  rule_id: string;
  file_path: string;
  baseline_evidence: Record<string, unknown>;
  rescan_evidence: Record<string, unknown>;
  line_shift: number;
  similarity_score: number;
  explanation: string;
  created_at: string;
}

export interface VerificationRegressionCheck {
  id: string;
  job_id: string;
  workspace_id: string;
  check_name: string;
  status: RegressionCheckStatus;
  duration_ms: number;
  output_summary: string;
  error_details?: string | null;
  created_at: string;
}

export interface VerificationReview {
  id: string;
  job_id: string;
  workspace_id: string;
  finding_id: string;
  reviewer_id: string;
  decision: "accepted" | "rejected";
  rationale: string;
  finding_status_after: string;
  reviewed_at: string;
}

export interface VerificationJob {
  id: string;
  workspace_id: string;
  asset_id: string;
  finding_id: string;
  proposal_id?: string | null;
  application_id?: string | null;
  rescan_id?: string | null;
  status: VerificationJobStatus;
  vulnerability_status: VulnerabilityVerificationStatus;
  regression_status: RegressionCheckStatus;
  scanner_status: ScannerVerificationStatus;
  test_status: string;
  policy_verdict: VerificationPolicyVerdict;
  policy_version: string;
  policy_reasons: string[];
  baseline_snapshot: Record<string, unknown>;
  source_revision?: string | null;
  target_revision?: string | null;
  patch_hash?: string | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  comparisons?: VerificationComparison[];
  regression_checks?: VerificationRegressionCheck[];
  reviews?: VerificationReview[];
  finding?: Finding;
  asset?: Asset;
}

export interface VerificationListResponse {
  items: VerificationJob[];
  total: number;
}

// Stage 10: Security Reports & Executive Dashboard
export type ReportType =
  | "executive_summary"
  | "technical_vulnerability"
  | "remediation_progress"
  | "verification_regression"
  | "asset_security_posture";

export type ReportFormat = "json" | "pdf" | "html" | "markdown";
export type ReportStatus = "generating" | "completed" | "ready" | "failed";

export interface AssetMetrics {
  total: number;
  authorized: number;
  unauthorized: number;
  by_criticality: Record<string, number>;
}

export interface ScanMetrics {
  total: number;
  completed: number;
  failed: number;
  running: number;
  latest_scan_at: string | null;
}

export interface FindingMetrics {
  total: number;
  open: number;
  fixed: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
}

export interface RiskMetrics {
  current_score: number | null;
  risk_band: string | null;
  formula_version: string;
  is_calculated: boolean;
  critical_attack_paths_count: number;
}

export interface RemediationMetrics {
  total_proposals: number;
  awaiting_approval: number;
  approved: number;
  applied: number;
  rejected: number;
}

export interface VerificationMetrics {
  total_jobs: number;
  verified_candidates: number;
  human_accepted: number;
  failed_or_blocked: number;
  latest_verification_at: string | null;
}

export interface DashboardMetricsResponse {
  workspace_id: string;
  generated_at: string;
  has_completed_scans: boolean;
  data_disclaimer: string;
  assets: AssetMetrics;
  scans: ScanMetrics;
  findings: FindingMetrics;
  risk: RiskMetrics;
  remediations: RemediationMetrics;
  verifications: VerificationMetrics;
  recent_activity: Array<Record<string, unknown>>;
}

export interface FindingTrendPoint {
  date: string;
  new_findings: number;
  fixed_findings: number;
  open_findings: number;
}

export interface RiskTrendPoint {
  date: string;
  score: number;
  band: string;
}

export interface RemediationTrendPoint {
  date: string;
  proposed: number;
  approved: number;
  applied: number;
}

export interface DashboardTrendsResponse {
  workspace_id: string;
  trend_window_days: number;
  data_available: boolean;
  message: string | null;
  findings_trend: FindingTrendPoint[];
  risk_score_trend: RiskTrendPoint[];
  remediation_trend: RemediationTrendPoint[];
}

export interface ReportCreateRequest {
  report_type: ReportType;
  title?: string;
  description?: string;
  format?: ReportFormat;
  period_start?: string;
  period_end?: string;
  asset_ids?: string[];
  severities?: string[];
  include_ai_summary?: boolean;
}

export interface SecurityReport {
  id: string;
  workspace_id: string;
  scan_id?: string | null;
  report_type: ReportType | string;
  title: string;
  description?: string | null;
  format: ReportFormat | string;
  status: ReportStatus | string;
  generated_by: string;
  period_start?: string | null;
  period_end?: string | null;
  data_cutoff_at: string;
  schema_version: string;
  completeness_status: string;
  parameters: Record<string, unknown>;
  snapshot_data: Record<string, any>;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface ReportListResponse {
  items: SecurityReport[];
  total: number;
}

export interface ReportExportResponse {
  report_id: string;
  format: string;
  file_name: string;
  content_type: string;
  download_url?: string;
  data_cutoff_at: string;
}

// Stage 11: Notifications & Controlled Workflow Automation
export interface NotificationItem {
  id: string;
  workspace_id: string;
  user_id: string;
  event_id?: string | null;
  category: "scans" | "findings" | "remediation" | "verification" | "reports" | "risk" | "general" | string;
  type: string;
  title: string;
  message: string;
  resource_type?: string | null;
  resource_id?: string | null;
  link_url?: string | null;
  channels: string[];
  read_at?: string | null;
  sent_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
}

export interface NotificationPreferences {
  id: string;
  workspace_id: string;
  user_id: string;
  categories: {
    scans: boolean;
    findings: boolean;
    remediation: boolean;
    verification: boolean;
    reports: boolean;
    risk: boolean;
    [key: string]: boolean;
  };
  channels: {
    in_app: boolean;
    email: boolean;
    [key: string]: boolean;
  };
  min_severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  created_at: string;
  updated_at: string;
}

export interface NotificationRule {
  id: string;
  workspace_id: string;
  name: string;
  event_type: string;
  enabled: boolean;
  channels: string[];
  recipient_roles: string[];
  severity_filter: string[];
  dedup_window_minutes: number;
  rate_limit_per_hour: number;
  created_at: string;
}

export interface WorkflowRunItem {
  id: string;
  workspace_id: string;
  workflow_name: string;
  trigger_event_id?: string | null;
  action_name: string;
  status: "queued" | "running" | "completed" | "failed" | string;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  idempotency_key?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface WorkflowRunListResponse {
  items: WorkflowRunItem[];
  total: number;
}






