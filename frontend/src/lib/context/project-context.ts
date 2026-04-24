// lib/context/project-context.ts
import { notFound } from "next/navigation";
import { getBaseApiUrl } from "@/lib/config";

export interface ProjectContextData {
  project_id: string;
  project_name: string;
  status: string;
}

export async function getProjectContext(slug: string): Promise<ProjectContextData> {
  // 1. Validate input
  if (!slug || slug === "undefined") {
    console.error("❌ Critical: Attempted to resolve undefined slug");
    notFound(); 
  }

  try {
    // 2. Call the Universal Backend Endpoint
    const apiUrl = getBaseApiUrl();
    const res = await fetch(`${apiUrl}/api/resolve/slug/${slug}`, {
      method: "GET",
      cache: "no-store", // Always fetch fresh data
    });

    if (!res.ok) {
      if (res.status === 404) return notFound();
      throw new Error(`Resolver API Error: ${res.status}`);
    }

    return await res.json();
  } catch (error) {
    console.error("❌ Failed to resolve project context:", error);
    throw error; // Let the page error boundary handle it
  }
}