/**
 * Gate contracts — mirrors shared/gate_contracts.py (Company Brain v1.0.0).
 */

export type GateName = 'resolve' | 'complete' | 'clarify' | 'commit';
export type GateStatus = 'ok' | 'needs_human' | 'blocked';
export type GapSeverity = 'blocking' | 'choice' | 'hint';

export interface GapItem {
  field: string;
  question: string;
  candidates?: string[];
  severity: GapSeverity;
  rule_id?: string;
  doctype?: string;
  entity_key?: string;
}

export interface HonestySlice {
  valid: boolean;
  errors: string[];
  warnings: string[];
  corrections?: Array<Record<string, unknown>>;
}

export interface GateResult {
  gate: GateName;
  status: GateStatus;
  gaps: GapItem[];
  honesty?: HonestySlice;
  resolved?: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

/** Fields OS should never ask the user for (KB erp_autofill_fields). */
export const ERP_AUTOFILL_FIELDS = new Set([
  'naming_series',
  'company',
  'currency',
  'conversion_rate',
  'selling_price_list',
  'buying_price_list',
  'price_list_currency',
  'plc_conversion_rate',
  'order_type',
  'transaction_date',
  'posting_date',
  'status',
  'title',
]);

/** Skip phrases for optional business fields (delivery date, etc.). */
export const OPTIONAL_FIELD_SKIP_PHRASES = [
  'skip',
  'not needed',
  'not required',
  'no delivery',
  'no delivery date',
  'none',
  'n/a',
  'na',
  'no thanks',
  'omit',
] as const;

export function isAutofillField(fieldname: string): boolean {
  return ERP_AUTOFILL_FIELDS.has(fieldname);
}
