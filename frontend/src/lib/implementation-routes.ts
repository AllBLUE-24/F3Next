/**
 * Maps IS workflow stages to the correct implementation UI route.
 */

export type ImplementationStep = 'upload' | 'analyze' | 'validate' | 'import';

const VALIDATE_STAGES = new Set(['awaiting_validation_submission']);

const IMPORT_STAGES = new Set([
  'awaiting_sandbox_approval',
  'importing',
  'import_blocked',
  'complete',
  'complete_with_errors',
]);

const ANALYZE_STAGES = new Set([
  'analyzing',
  'awaiting_f3iche_confirmation',
  'building_profile',
  'awaiting_data_readiness_confirmation',
  'mapping',
  'mapping_files',
  'awaiting_mapping_confirmation',
  'refining_mapping',
  'validating',
]);

export function stageToStep(stage: string | null | undefined): ImplementationStep {
  if (!stage) return 'upload';
  if (VALIDATE_STAGES.has(stage)) return 'validate';
  if (IMPORT_STAGES.has(stage)) return 'import';
  if (ANALYZE_STAGES.has(stage)) return 'analyze';
  if (stage === 'awaiting_files' || stage === 'error' || stage === 'infected_halt') return 'upload';
  return 'analyze';
}

export function implementationHref(
  base: string,
  step: ImplementationStep,
  jobId: string,
): string {
  const q = `?jobId=${encodeURIComponent(jobId)}`;
  switch (step) {
    case 'upload':
      return `${base}/upload`;
    case 'analyze':
      return `${base}/analyze${q}`;
    case 'validate':
      return `${base}/validate${q}`;
    case 'import':
      return `${base}/import${q}`;
  }
}

export function stageToHref(base: string, stage: string | null | undefined, jobId: string): string {
  return implementationHref(base, stageToStep(stage), jobId);
}
