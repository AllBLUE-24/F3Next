'use client';

// src/contexts/ImplementationContext.tsx

import { createContext, useContext, useCallback, useEffect, useState } from 'react';
import type {
  ImplementationContextValue,
  ImplementationSession,
  DeploymentState,
  CompanyProfile,
  ValidationItem,
  SandboxInstance,
} from '@/types/implementation';

const ImplementationContext = createContext<ImplementationContextValue | null>(null);

export function useImplementation(): ImplementationContextValue {
  const ctx = useContext(ImplementationContext);
  if (!ctx) throw new Error('useImplementation must be used inside ImplementationProvider');
  return ctx;
}

interface Props {
  session: ImplementationSession;
  initialDeployment: DeploymentState;
  children: React.ReactNode;
}

export function ImplementationProvider({ session, initialDeployment, children }: Props) {
  const [deployment, setDeployment] = useState<DeploymentState>(initialDeployment);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [validationItems, setValidationItems] = useState<ValidationItem[]>([]);
  const [sandbox, setSandbox] = useState<SandboxInstance | null>(null);

  const refreshDeployment = useCallback(async () => {
    try {
      const base = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${base}/api/deployment/${session.instanceId}`);
      if (!res.ok) return;
      const data: DeploymentState = await res.json();
      setDeployment(data);
    } catch {
      // silently fail — next poll will retry
    }
  }, [session.instanceId]);

  // Poll deployment status until ready or failed
  useEffect(() => {
    if (deployment.status === 'ready' || deployment.status === 'failed') return;

    const interval = setInterval(refreshDeployment, 5000);
    return () => clearInterval(interval);
  }, [deployment.status, refreshDeployment]);

  return (
    <ImplementationContext.Provider
      value={{ session, deployment, profile, validationItems, sandbox, refreshDeployment }}
    >
      {children}
    </ImplementationContext.Provider>
  );
}