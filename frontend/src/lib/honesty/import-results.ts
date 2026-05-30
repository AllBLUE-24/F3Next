/**
 * Import results honesty — aggregate step/record counts from import-results API.
 */

export interface ImportResultRow {
  phase: string;
  step_number: number;
  doctype: string;
  action: string;
  status: string;
  records_attempted: number;
  records_succeeded: number;
  records_failed: number;
  error_message: string | null;
  erp_doc_name?: string | null;
}

export interface ImportResultsSummary {
  stepsTotal: number;
  stepsSucceeded: number;
  stepsFailed: number;
  recordsAttempted: number;
  recordsSucceeded: number;
  recordsFailed: number;
  hasPartialFailure: boolean;
}

export function summarizeImportResults(rows: ImportResultRow[]): ImportResultsSummary {
  let stepsSucceeded = 0;
  let stepsFailed = 0;
  let recordsAttempted = 0;
  let recordsSucceeded = 0;
  let recordsFailed = 0;

  for (const row of rows) {
    const rowFailed =
      row.status === 'error' ||
      row.status === 'failed' ||
      (row.records_failed ?? 0) > 0;
    if (rowFailed) {
      stepsFailed += 1;
    } else if (row.status === 'success' || row.status === 'ok' || row.records_succeeded > 0) {
      stepsSucceeded += 1;
    }
    recordsAttempted += row.records_attempted ?? 0;
    recordsSucceeded += row.records_succeeded ?? 0;
    recordsFailed += row.records_failed ?? 0;
  }

  return {
    stepsTotal: rows.length,
    stepsSucceeded,
    stepsFailed,
    recordsAttempted,
    recordsSucceeded,
    recordsFailed,
    hasPartialFailure: stepsFailed > 0 || recordsFailed > 0,
  };
}

export type ImportHonestyState = 'in_progress' | 'success' | 'partial' | 'blocked';

export function resolveImportHonestyState(
  stage: string | null,
  summary: ImportResultsSummary,
): ImportHonestyState {
  if (stage === 'import_blocked') return 'blocked';
  if (stage === 'importing') return 'in_progress';
  if (stage === 'complete_with_errors') return 'partial';
  if (stage === 'complete') {
    return summary.hasPartialFailure ? 'partial' : 'success';
  }
  return 'in_progress';
}

export function importHonestyHeadline(state: ImportHonestyState, summary: ImportResultsSummary): {
  title: string;
  subtitle: string;
} {
  switch (state) {
    case 'success':
      return {
        title: "You're live.",
        subtitle: 'Your data has been imported into your live ERPNext instance.',
      };
    case 'partial':
      return {
        title: 'Import finished with errors.',
        subtitle: summary.stepsTotal > 0
          ? `Imported ${summary.stepsSucceeded} of ${summary.stepsTotal} steps — ${summary.stepsFailed} failed. See details below.`
          : 'Some records failed to import. Review the results below before using the live instance.',
      };
    case 'blocked':
      return {
        title: 'Import blocked.',
        subtitle: 'Critical setup gaps must be resolved before live import can run.',
      };
    case 'in_progress':
    default:
      return {
        title: 'Your ERP is ready.',
        subtitle: 'Review your live instance below. When ready, approve to run the live import.',
      };
  }
}
