// PATH: src/components/implementation/ImplementationServerProvider.tsx

import { notFound } from 'next/navigation';
import { ImplementationProvider } from '@/contexts/ImplementationContext';
import type { ImplementationSession, DeploymentState } from '@/types/implementation';

// ─── Dev mock — only used when API_BASE_URL is not set or fetch fails in dev ───
function mockSession(companySlug: string, userSlug: string): ImplementationSession {
  return {
    id: 'dev-session-001',
    companySlug,
    userSlug,
    currentStep: 'upload',
    instanceId: 'dev-instance-001',
    analysisJobId: null,
    createdAt: new Date().toISOString(),
  };
}

function mockDeployment(): DeploymentState {
  return {
    status: 'deploying',
    progress: 47,
    instanceUrl: null,
    region: 'ap-south-1',
    erpSoftware: 'ERPNext',
    startedAt: new Date().toISOString(),
    readyAt: null,
  };
}

const IS_DEV = process.env.NODE_ENV === 'development';
// ────────────────────────────────────────────────────────────────────────────────

async function fetchSession(
  companySlug: string,
  userSlug: string
): Promise<ImplementationSession | null> {
  if (!process.env.API_BASE_URL) {
    if (IS_DEV) return mockSession(companySlug, userSlug);
    return null;
  }

  try {
    const res = await fetch(
      `${process.env.API_BASE_URL}/implementation/session?company=${companySlug}&user=${userSlug}`,
      {
        cache: 'no-store',
        headers: { 'x-internal-secret': process.env.INTERNAL_SECRET! },
        // Fail fast in dev so the page doesn't hang
        signal: AbortSignal.timeout(IS_DEV ? 3000 : 10000),
      }
    );
    if (!res.ok) return IS_DEV ? mockSession(companySlug, userSlug) : null;
    return res.json();
  } catch {
    // Backend unreachable — use mock in dev, hard fail in prod
    if (IS_DEV) return mockSession(companySlug, userSlug);
    return null;
  }
}

async function fetchDeploymentState(instanceId: string): Promise<DeploymentState> {
  if (!process.env.API_BASE_URL) {
    if (IS_DEV) return mockDeployment();
  }

  try {
    const res = await fetch(
      `${process.env.API_BASE_URL}/deployment/${instanceId}`,
      {
        cache: 'no-store',
        headers: { 'x-internal-secret': process.env.INTERNAL_SECRET! },
        signal: AbortSignal.timeout(IS_DEV ? 3000 : 10000),
      }
    );
    if (!res.ok) throw new Error();
    return res.json();
  } catch {
    return IS_DEV ? mockDeployment() : {
      status: 'pending',
      progress: 0,
      instanceUrl: null,
      region: 'ap-south-1',
      erpSoftware: 'ERPNext',
      startedAt: new Date().toISOString(),
      readyAt: null,
    };
  }
}

interface Props {
  companySlug: string;
  userSlug: string;
  children: React.ReactNode;
}

export async function ImplementationServerProvider({ companySlug, userSlug, children }: Props) {
  const session = await fetchSession(companySlug, userSlug);

  // In production with no session → genuine 404
  // In dev this never happens because mockSession always returns a value
  if (!session) notFound();

  const deployment = await fetchDeploymentState(session.instanceId);

  return (
    <ImplementationProvider session={session} initialDeployment={deployment}>
      {children}
    </ImplementationProvider>
  );
}