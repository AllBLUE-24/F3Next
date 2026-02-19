'use client';

// src/hooks/implementation/useAnalysis.ts

import { useCallback, useEffect, useRef, useState } from 'react';
import type { AnalysisTask, CompanyProfile } from '@/types/implementation';

interface AnalysisState {
  tasks: AnalysisTask[];
  profile: CompanyProfile | null;
  isComplete: boolean;
  needsInput: boolean;
  error: string | null;
}

export function useAnalysis(jobId: string | null) {
  const [state, setState] = useState<AnalysisState>({
    tasks: [],
    profile: null,
    isComplete: false,
    needsInput: false,
    error: null,
  });
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const poll = useCallback(async () => {
    if (!jobId) return;
    try {
      const res = await fetch(`/api/analysis/${jobId}`);
      if (!res.ok) throw new Error('Failed to fetch analysis status');
      const data = await res.json();
      setState({
        tasks: data.tasks,
        profile: data.profile,
        isComplete: data.status === 'complete',
        needsInput: data.status === 'needs_input',
        error: null,
      });
      // Stop polling once done
      if (data.status === 'complete' || data.status === 'needs_input') {
        if (intervalRef.current) clearInterval(intervalRef.current);
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

  return state;
}