'use client';

// src/hooks/implementation/useDeploymentStatus.ts

import { useCallback, useEffect, useState } from 'react';
import type { DeploymentState } from '@/types/implementation';

export function useDeploymentStatus(instanceId: string, initial: DeploymentState) {
  const [state, setState] = useState<DeploymentState>(initial);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`/api/deployment/${instanceId}`);
      if (!res.ok) return;
      setState(await res.json());
    } catch { /* retry next tick */ }
  }, [instanceId]);

  useEffect(() => {
    if (state.status === 'ready' || state.status === 'failed') return;
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [state.status, refresh]);

  return state;
}