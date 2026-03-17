"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
// 🟢 Import your existing API hook
import { resolveProjectSlug } from "@/lib/api/hooks_api"; 

export default function ConfigApplyPage() {
  // Extract slugs from the URL
  const params = useParams();
  const companySlug = params.companySlug as string;
  const userSlug = params.userSlug as string;

  const [projectId, setProjectId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("Resolving Project...");

  // 1. Resolver Step: Use existing hook to get Project ID
  useEffect(() => {
    async function init() {
      try {
        if (!companySlug) return;
        
        // 🟢 Calls resolver.py via hooks_api.ts
        const data = await resolveProjectSlug(companySlug);
        
        if (data?.project_id) {
            setProjectId(data.project_id);
            setStatus("Ready to Apply Configuration");
        } else {
            setStatus("Error: Project ID not returned.");
        }
      } catch (err) {
        console.error(err);
        setStatus("Failed to resolve project context.");
      }
    }
    init();
  }, [companySlug]);

  // 2. Trigger Step: Start the Agent
  const handleApplyConfig = async () => {
    if (!projectId) return;

    setLoading(true);
    setStatus("Initiating Config Agent...");

    try {
      // Calls the NEW backend endpoint (defined below)
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/config_apply/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "API Error");
      }

      setStatus("Agent Started! Deployment in progress...");
    } catch (error) {
      setStatus("Failed to start agent. Check console.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white p-6">
      <div className="w-full max-w-lg border border-gray-200 rounded-xl shadow-sm p-8">
        <h1 className="text-2xl font-bold mb-2">Finalize Configuration</h1>
        <p className="text-gray-500 mb-6">
          Deploying ERPNext for <span className="font-semibold text-black">{companySlug}</span>
        </p>
        
        {/* Status Box */}
        <div className="bg-gray-50 border border-gray-100 p-4 rounded-lg mb-6 font-mono text-sm text-gray-700">
          Status: {status}
          <br/>
          <span className="text-xs text-gray-400 mt-1 block">PID: {projectId || "Waiting..."}</span>
        </div>

        <button
          onClick={handleApplyConfig}
          disabled={!projectId || loading}
          className={`w-full py-4 rounded-lg font-semibold text-white transition-all
            ${!projectId || loading 
              ? "bg-gray-300 cursor-not-allowed" 
              : "bg-black hover:bg-gray-800"
            }`}
        >
          {loading ? "Starting Agent..." : "🚀 Launch Config-Apply Agent"}
        </button>
      </div>
    </div>
  );
}