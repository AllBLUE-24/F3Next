import { describe, expect, it } from 'vitest';
import {
  summarizeImportResults,
  resolveImportHonestyState,
  importHonestyHeadline,
  type ImportResultRow,
} from '@/lib/honesty/import-results';

const okRow: ImportResultRow = {
  phase: 'B',
  step_number: 1,
  doctype: 'Item',
  action: 'create',
  status: 'success',
  records_attempted: 10,
  records_succeeded: 10,
  records_failed: 0,
  error_message: null,
};

const failRow: ImportResultRow = {
  phase: 'C',
  step_number: 2,
  doctype: 'Work Order',
  action: 'create',
  status: 'error',
  records_attempted: 2,
  records_succeeded: 0,
  records_failed: 2,
  error_message: 'BOM must be submitted',
};

describe('import honesty', () => {
  it('detects partial failure when stage is complete but steps failed', () => {
    const summary = summarizeImportResults([okRow, failRow]);
    expect(summary.hasPartialFailure).toBe(true);
    expect(summary.stepsFailed).toBe(1);
    expect(resolveImportHonestyState('complete', summary)).toBe('partial');
  });

  it('never labels full success when any step failed', () => {
    const summary = summarizeImportResults([okRow, failRow]);
    const headline = importHonestyHeadline('partial', summary);
    expect(headline.title.toLowerCase()).toContain('error');
    expect(headline.subtitle).toContain('1 failed');
  });

  it('allows green success only when all steps ok', () => {
    const summary = summarizeImportResults([okRow]);
    expect(resolveImportHonestyState('complete', summary)).toBe('success');
    const headline = importHonestyHeadline('success', summary);
    expect(headline.title).toContain('live');
  });
});

describe('gate copy', () => {
  it('maps unknown_customer to plain language', async () => {
    const { friendlyRuleMessage } = await import('@/lib/copy/gate-copy');
    expect(friendlyRuleMessage('unknown_customer', 'raw')).toMatch(/customer/i);
  });
});

describe('clarification mapper', () => {
  it('extracts candidates from confirmation request', async () => {
    const { clarificationFromConfirmationRequest } = await import('@/lib/api/gate-mappers');
    const ui = clarificationFromConfirmationRequest({
      question: "Which customer?",
      round: 1,
      field: 'customer',
      candidates: ['Acme Ltd', 'Beta Co'],
    });
    expect(ui?.candidates).toEqual(['Acme Ltd', 'Beta Co']);
    expect(ui?.severity).toBe('choice');
  });
});
