/**
 * Human-readable copy for gate errors and rule IDs (branch 05 UX).
 */

const RULE_COPY: Record<string, string> = {
  mandatory_fields: 'A required field is missing.',
  unknown_customer: "This customer isn't in your ERP yet. Pick one from the list or add it in ERPNext.",
  unknown_supplier: "This supplier isn't in your ERP yet. Pick one from the list or add it in ERPNext.",
  unknown_item: "This item isn't in your ERP yet. Pick one from the list or add it in ERPNext.",
  unknown_warehouse: "This warehouse isn't in your ERP yet. Pick one from the list or add it in ERPNext.",
  unknown_link: "A linked record wasn't found on your ERP site.",
  is_link_missing_post_ler: "A linked record wasn't found on your ERP site. Fix the source file or create the record in ERPNext.",
  invalid_company_link: 'Company must be a live ERPNext company name, not a workspace slug.',
  child_table_validation: 'Line items need at least one row with item and quantity.',
};

const FIELD_AUTOFILL_HINT: Record<string, string> = {
  title: "We'll set the order title automatically.",
  naming_series: "We'll choose the naming series from your ERP defaults.",
  company: "We'll use your default company from ERPNext.",
  transaction_date: "We'll set the transaction date to today.",
  posting_date: "We'll set the posting date to today.",
};

export function friendlyRuleMessage(ruleId: string | undefined, fallback: string): string {
  if (!ruleId) return fallback;
  const mapped = RULE_COPY[ruleId];
  if (mapped) return mapped;
  if (ruleId.includes('customer')) return RULE_COPY.unknown_customer;
  if (ruleId.includes('supplier')) return RULE_COPY.unknown_supplier;
  if (ruleId.includes('item')) return RULE_COPY.unknown_item;
  return fallback;
}

export function friendlyFieldHint(field: string, message: string): string {
  const hint = FIELD_AUTOFILL_HINT[field];
  if (hint && /mandatory|required|missing/i.test(message)) {
    return hint;
  }
  return message;
}

export function friendlyNetworkError(context: 'confirm' | 'answer' | 'command', raw: string): string {
  if (/failed to fetch|network|load failed/i.test(raw)) {
    if (context === 'confirm') {
      return "Couldn't reach the server. Check your connection and retry Confirm.";
    }
    if (context === 'answer') {
      return "Couldn't reach the server. Check your connection and retry your answer.";
    }
    return "Couldn't reach the server. Check your connection and try again.";
  }
  if (/^\[\d+\]/.test(raw)) {
    return raw.replace(/^\[\d+\]\s*/, '');
  }
  return raw;
}
