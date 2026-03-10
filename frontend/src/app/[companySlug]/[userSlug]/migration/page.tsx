// src/app/[companySlug]/[userSlug]/migration/page.tsx
import { getProjectContext } from "@/lib/context/project-context";
import MigrationClient from "@/components/shared/MigrationClient"; 

// 1. UPDATE THE INTERFACE
// In Next.js 15+, params is a Promise, not a direct object.
interface PageProps {
  params: Promise<{
    companySlug: string;
    userSlug: string;
  }>;
}

export default async function MigrationPage({ params }: PageProps) {
  // 2. AWAIT THE PARAMS
  // We must unwrap the promise to get the actual strings
  const resolvedParams = await params;
  const { companySlug } = resolvedParams;

  // 3. NOW PASS THE STRING TO YOUR RESOLVER
  const projectContext = await getProjectContext(companySlug);

  return (
    <main className="min-h-screen bg-gray-50">
      <MigrationClient 
        projectId={projectContext.project_id} 
        companySlug={companySlug} 
      />
    </main>
  );
}