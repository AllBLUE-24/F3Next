// PATH: src/components/implementation/ImplementationServerProvider.tsx

import { notFound } from 'next/navigation';
import { ImplementationProvider } from '@/contexts/ImplementationContext';
import type { ImplementationSession, DeploymentState } from '@/types/implementation';
import { getProjectContext } from '@/lib/context/project-context';

const IS_DEV = process.env.NODE_ENV === 'development';
const API_BASE = 'http://backend_api:8000';

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

async function fetchDeploymentState(instanceId: string): Promise<DeploymentState> {
  try {
    const res = await fetch(
      `${API_BASE}/api/deployment/${instanceId}`,
      {
        cache: 'no-store',
        headers: { 'x-internal-secret': process.env.INTERNAL_SECRET || '' },
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
  // 1. Universal Slug Resolver (Direct Postgres access via Cache)
  const context = await getProjectContext(companySlug);

  if (!context) notFound();

  // 2. Synthesize Context into the required Provider Session schema
  const session: ImplementationSession = {
    id: context.project_id,
    companySlug,
    userSlug,
    currentStep: context.status === 'created' ? 'upload' : 'analyze',
    instanceId: context.project_id, // Hardlinking deployment instance to project uuid
    analysisJobId: null,
    createdAt: new Date().toISOString(),
  };

  const deployment = await fetchDeploymentState(session.instanceId);

  return (
    <ImplementationProvider session={session} initialDeployment={deployment}>
      {children}
    </ImplementationProvider>
  );
}