/**
 * Implementation system API client
 * F3iche, signals, profile, target structure, mapping, validation, import
 */

const getBaseUrl = () => '';

export interface SignalsInferResult {
  f3iche: string;
  confidence: number;
  collected_signals: string[];
}

export interface F3icheVerifyResult {
  is_match: boolean;
  status: 'matched' | 'mismatch' | 'pending_clarification';
  clarification_message: string | null;
}

export interface TargetStructure {
  f3iche: string;
  industry: string | null;
  required_doctypes: string[];
  setup_steps: Array<{ doctype: string; layer: string; phase: string }>;
  import_phases: Record<string, string[]>;
  validation_rules: Record<string, unknown>;
}

export interface MapFileResult {
  doctype: string | null;
  field_mapping: Record<string, string>;
  rows: Record<string, unknown>[];
  inferred_doctype: string | null;
  source_columns: string[];
}

export interface ValidationReport {
  overall: 'pass' | 'fail';
  timestamp: string;
  checks: Array<{ doctype: string; status: string; errors: string[]; warnings: string[] }>;
  errors: string[];
  warnings: string[];
}

export interface ImportPlan {
  status: 'ready' | 'blocked';
  phases: Array<{
    phase: string;
    name: string;
    description: string;
    steps: Array<{ doctype: string; data: unknown; action: string }>;
  }>;
  total_steps: number;
}

export async function inferF3icheFromFiles(
  projectId: string,
  uploadedFiles: Array<{ file_name: string; object_path?: string }>,
  fileContents?: Record<string, string>
): Promise<SignalsInferResult> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/signals/infer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      uploaded_files: uploadedFiles,
      file_contents: fileContents,
    }),
  });
  if (!res.ok) throw new Error('Failed to infer F3iche');
  const data = await res.json();
  return data;
}

export async function verifyF3icheMatch(
  projectId: string,
  f3icheUser: string,
  f3icheSignals: string,
  confidence = 0
): Promise<F3icheVerifyResult> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/f3iche/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      f3iche_user: f3icheUser,
      f3iche_signals: f3icheSignals,
      confidence,
    }),
  });
  if (!res.ok) throw new Error('Failed to verify F3iche');
  const data = await res.json();
  return data;
}

export async function buildTargetStructure(
  projectId: string,
  f3iche: string,
  industry?: string
): Promise<{ target_structure: TargetStructure }> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/target-structure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      f3iche,
      industry,
    }),
  });
  if (!res.ok) throw new Error('Failed to build target structure');
  return res.json();
}

export async function mapFileToErpNext(
  content: string,
  filename: string,
  doctypeHint?: string
): Promise<MapFileResult> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/map-file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content,
      filename,
      doctype_hint: doctypeHint,
    }),
  });
  if (!res.ok) throw new Error('Failed to map file');
  return res.json();
}

export async function validateMappedData(
  projectId: string,
  mappedData: Record<string, unknown>,
  targetStructure: Record<string, unknown>
): Promise<{ validation_report: ValidationReport }> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      mapped_data: mappedData,
      target_structure: targetStructure,
    }),
  });
  if (!res.ok) throw new Error('Failed to validate');
  return res.json();
}

export async function buildImportPlan(
  projectId: string,
  targetStructure: Record<string, unknown>,
  mappedData: Record<string, unknown>,
  validationReport: Record<string, unknown>
): Promise<{ import_plan: ImportPlan }> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/import/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      target_structure: targetStructure,
      mapped_data: mappedData,
      validation_report: validationReport,
    }),
  });
  if (!res.ok) throw new Error('Failed to build import plan');
  return res.json();
}

export async function getCompanyProfile(projectId: string): Promise<{
  profile: Record<string, unknown>;
  project_id: string;
}> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/profile/${projectId}`);
  if (!res.ok) throw new Error('Failed to get profile');
  return res.json();
}

export async function updateCompanyProfile(
  payload: {
    project_id: string;
    f3iche: string;
    industry: string;
    industry_sub?: string;
    company_size?: string;
    company_name?: string;
    f3iche_user?: string;
    f3iche_signals?: string;
    f3iche_match_status?: string;
    uploaded_files?: Array<Record<string, unknown>>;
    collected_signals?: string[];
    target_structure?: Record<string, unknown>;
    field_mappings?: Record<string, unknown>;
    validation_report?: Record<string, unknown>;
    import_phase?: string;
    action?: string;
  }
): Promise<{ profile: Record<string, unknown>; version: number }> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/profile/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update profile');
  return res.json();
}

export async function listF3iches(): Promise<{
  f3iches: Array<{ id: string; name: string; description: string }>;
}> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/f3iche/list`);
  if (!res.ok) throw new Error('Failed to list F3iches');
  return res.json();
}


// ── Validate Preview ──────────────────────────────────────────────────────────

export interface ValidatePreviewDoctype {
  doctype: string;
  source_file: string | null;
  total_rows: number;
  total_mapped_fields: number;
  validation_status: string;
  errors: Array<{ message: string; severity: string; field: string }>;
  warnings: Array<{ message: string; severity: string; field: string }>;
  columns: string[];
  records: Record<string, unknown>[];
}

export interface ValidatePreviewData {
  profile: Record<string, unknown>;
  doctypes: ValidatePreviewDoctype[];
  import_summary: Record<string, string[]>;
  validation_overall: string;
}

export async function getValidatePreview(projectId: string): Promise<ValidatePreviewData> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/validate-preview/${projectId}`);
  if (!res.ok) throw new Error('Failed to fetch validation preview');
  return res.json();
}

export async function sendSandboxApproved(projectId: string, dryRun = false): Promise<void> {
  const res = await fetch(`${getBaseUrl()}/api/implementation/signal/sandbox-approved`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, dry_run: dryRun }),
  });
  if (!res.ok) throw new Error('Failed to send sandbox approved signal');
}
