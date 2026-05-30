/**
 * Map API payloads to GateResult / GapItem shapes.
 */

import type { GapItem, GateResult, GapSeverity } from '@/types/gates';

export function mapGapFromApi(raw: Record<string, unknown>): GapItem {
  const severity = (raw.severity as GapSeverity) || 'blocking';
  const candidates = Array.isArray(raw.candidates)
    ? raw.candidates.map(String).filter(Boolean)
    : undefined;
  return {
    field: String(raw.field || raw.entity_key || 'field'),
    question: String(raw.question || ''),
    candidates: candidates?.length ? candidates : undefined,
    severity,
    rule_id: raw.rule_id ? String(raw.rule_id) : undefined,
    doctype: raw.doctype ? String(raw.doctype) : undefined,
    entity_key: raw.entity_key ? String(raw.entity_key) : undefined,
  };
}

export function mapGateResultFromApi(raw: Record<string, unknown>): GateResult {
  const gapsRaw = Array.isArray(raw.gaps) ? raw.gaps : [];
  const honestyRaw = raw.honesty as Record<string, unknown> | undefined;
  return {
    gate: (raw.gate as GateResult['gate']) || 'clarify',
    status: (raw.status as GateResult['status']) || 'needs_human',
    gaps: gapsRaw.map((g) => mapGapFromApi(g as Record<string, unknown>)),
    honesty: honestyRaw
      ? {
          valid: Boolean(honestyRaw.valid ?? true),
          errors: (honestyRaw.errors as string[]) || [],
          warnings: (honestyRaw.warnings as string[]) || [],
        }
      : undefined,
    resolved: (raw.resolved as Record<string, unknown>) || {},
    meta: (raw.meta as Record<string, unknown>) || {},
  };
}

export interface ClarificationUiModel {
  question: string;
  round: number;
  field?: string;
  candidates: string[];
  severity: GapSeverity;
  lockedContext?: string[];
}

export function clarificationFromConfirmationRequest(
  cr: {
    question?: string | null;
    round?: number | null;
    field?: string | null;
    candidates?: string[] | null;
    severity?: string | null;
    preview?: { entities?: string[] | null } | null;
  } | null,
): ClarificationUiModel | null {
  if (!cr?.question) return null;
  return {
    question: cr.question,
    round: cr.round ?? 1,
    field: cr.field ?? undefined,
    candidates: (cr.candidates || []).filter(Boolean),
    severity: (cr.severity as GapSeverity) || (cr.candidates?.length ? 'choice' : 'blocking'),
    lockedContext: cr.preview?.entities?.filter(Boolean) as string[] | undefined,
  };
}
