'use client';

// src/hooks/implementation/useAnalysis.ts

import { useCallback, useEffect, useRef, useState } from 'react';
import type { AnalysisTask, CompanyProfile } from '@/types/implementation';

/**
 * All possible workflow stages from ImplementationWorkflow.
 * Grouped by UI behavior.
 */
const TERMINAL_STAGES = new Set(['complete', 'infected_halt', 'error']);
const NEEDS_INPUT_STAGES = new Set([
  'awaiting_f3iche_confirmation',
  'awaiting_file_mapping',
  'awaiting_validation_submission',
  'awaiting_sandbox_approval',
]);

interface AnalysisState {
  tasks: AnalysisTask[];
  profile: CompanyProfile | null;
  /** Raw stage string from the workflow */
  stage: string;
  /** Inferred F3iche ID (e.g. "trading_fmcg_distributor") */
  inferredNiche: string | null;
  /** Confidence 0–1 */
  confidence: number | null;
  isComplete: boolean;
  needsInput: boolean;
  error: string | null;
}

export function useAnalysis(jobId: string | null) {
  const [state, setState] = useState<AnalysisState>({
    tasks: [],
    profile: null,
    stage: '',
    inferredNiche: null,
    confidence: null,
    isComplete: false,
    needsInput: false,
    error: null,
  });
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const poll = useCallback(async () => {
    if (!jobId) return;
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';
      const res = await fetch(`${API_BASE}/api/implementation/state/${jobId}`);

      if (!res.ok) throw new Error('Failed to fetch analysis status');

      const data = await res.json();
      const stage: string = data.stage || '';

      setState({
        tasks: data.analysis_tasks || [],
        profile: data.profile || null,
        stage,
        inferredNiche: data.profile?.f3iche_signals || null,
        confidence: data.profile?.confidence ?? null,
        isComplete: TERMINAL_STAGES.has(stage),
        needsInput: NEEDS_INPUT_STAGES.has(stage),
        error: null,
      });

      // Stop Auto-polling on terminal or needs-input stages, but we can still manually refresh
      if (TERMINAL_STAGES.has(stage) || NEEDS_INPUT_STAGES.has(stage)) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } else {
        // Ensure polling is running if we are in an active stage
        if (!intervalRef.current) {
          intervalRef.current = setInterval(poll, 3000);
        }
      }
    } catch (err) {
      setState((prev) => ({ ...prev, error: 'Analysis polling error. Retrying...' }));
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    poll(); // immediate first call
    intervalRef.current = setInterval(poll, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, poll]);

  return { ...state, refresh: poll };
}