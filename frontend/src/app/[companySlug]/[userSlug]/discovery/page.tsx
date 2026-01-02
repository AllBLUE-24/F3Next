// app/dashboard/[slug]/page.tsx
// Note: NO "use client" here. This is a Server Component.

import DiscoveryClient from "@/components/shared/DiscoveryClient";
import { notFound } from "next/navigation";
import { getProjectContext } from "@/lib/context/project-context";

// 1. Define params to match your folder structure EXACTLY
interface PageProps {
  params: {
    companySlug: string;
    userSlug: string;
  };
}

// Define the shape of your backend response for the setup call
interface ProjectResolution {
  project_id: string;
  current_step: number;
  status: string;
}

// 1. Helper to fetch Project ID from Backend (Server-to-Server)
async function getProjectFromSlug(slug: string): Promise<ProjectResolution | null> {
  try {
    // This calls your FastAPI backend directly
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/resolve-slug/${slug}`, {
      method: "GET",
      cache: "no-store", // Ensure we get fresh data every time
      // Add internal headers for security if needed
      // headers: { "X-Internal-Secret": process.env.INTERNAL_SECRET } 
    });

    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error("Failed to resolve slug:", error);
    return null;
  }
}

export default async function DiscoveryPage({ params }: PageProps) {
 // 2. Use the correct param (companyslug)
 const resolvedParams = await params;
 const { companySlug } = resolvedParams;

 console.log(`🔍 Resolving Context for: ${companySlug}`);

 if (!companySlug) {
  console.error("❌ Slug is missing from URL parameters");
  return notFound();
}
 // 3. Use our Universal Helper
 const context = await getProjectContext(companySlug);

 // 4. Pass the resolved ID to the Client Component
 return (
  <DiscoveryClient 
    projectId={context.project_id} 
    // If your client needs the name, pass it here too
  />
);
}