import { use } from "react";
import { getProjectContext } from "@/lib/context/project-context";
import DynamicAgentClient from "./DynamicAgentClient";

export default function ImplementationWindowPage({
  params,
}: {
  params: Promise<{ companySlug: string; userSlug: string }>;
}) {
  const { companySlug } = use(params);
  
  // Actually, getProjectContext is async, but wait, Next.js requires awaiting params first anyway before awaiting data, or doing it concurrently.
  // We'll wrap in a component that fetches, or just fetch here.
  return <WindowWrapper companySlug={companySlug} />;
}

async function WindowWrapper({ companySlug }: { companySlug: string }) {
  try {
    const project = await getProjectContext(companySlug);
    return <DynamicAgentClient projectId={project.project_id} companySlug={companySlug} />;
  } catch (err) {
    return (
      <div className="flex h-full items-center justify-center text-red-500">
        Failed to load project context for {companySlug}. Make sure the company slug resolves correctly.
      </div>
    );
  }
}
