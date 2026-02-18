"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useRouter } from "next/navigation";

// Define response types
interface ProjectContext {
  project_id: string;
  project_name: string;
  status: string;
}

export default function InfraPage() {
  const params = useParams();
  const router = useRouter();

  // Safe Type Casting from URL
  const companySlug = typeof params.companySlug === 'string' ? params.companySlug : '';
  
  // State
  const [project, setProject] = useState<ProjectContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);
  const [deploySuccess, setDeploySuccess] = useState(false);
  const [error, setError] = useState("");

  // 1. RESOLVE PROJECT (On Load)
  useEffect(() => {
    async function resolveContext() {
      if (!companySlug) return;
      try {
        // Call your existing resolver endpoint
        const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/resolve/slug/${companySlug}`);
        setProject(res.data);
      } catch (err) {
        console.error("Failed to resolve project:", err);
        setError("Could not find project context.");
      } finally {
        setLoading(false);
      }
    }
    resolveContext();
  }, [companySlug]);

  // 2. HANDLER: TRIGGER INFRASTRUCTURE
  const handleDeploy = async () => {
    if (!project) return;
    setDeploying(true);
    setError("");

    try {
      // Call the NEW Backend Endpoint we defined above
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/deploy/infra`, {
        project_id: project.project_id,
        company_slug: companySlug,
        tier: "standard" // You could make this dynamic later
      });

      setDeploySuccess(true);
      
      // Optional: Start polling DB for "deployment_completed" status here if you want real-time updates
      
    } catch (err: any) {
      console.error("Deploy trigger failed:", err);
      setError(err.response?.data?.detail || "Failed to start deployment workflow.");
      setDeploying(false);
    }
  };

  // --- UI RENDERING ---

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="animate-pulse text-gray-400">Resolving Context...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-white">
        <div className="text-red-500 text-5xl mb-4">⚠️</div>
        <h1 className="text-xl font-bold text-gray-800">{error}</h1>
      </div>
    );
  }

  if (deploySuccess) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-white px-4">
        <div className="text-6xl mb-6 animate-bounce">🏗️</div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Deployment Initiated!</h1>
        <p className="text-gray-500 text-center max-w-md mb-8">
          The Infrastructure Agent is now provisioning your ERPNext server on EC2. 
          This usually takes 3-5 minutes.
        </p>
        
        <div className="w-full max-w-md bg-gray-50 p-4 rounded-lg border border-gray-200">
            <div className="flex items-center space-x-3 mb-2">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className="font-mono text-sm text-gray-700">Workflow: Running</span>
            </div>
            <p className="text-xs text-gray-400">Project ID: {project?.project_id}</p>
        </div>

        {/* You could add a button here to go to a "Dashboard" page */}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-20 px-6">
      <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden">
        
        {/* Header */}
        <div className="bg-gray-50 px-8 py-6 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-gray-900">Infrastructure Launchpad</h1>
          <p className="text-sm text-gray-500 mt-1">Ready to deploy ERPNext for <span className="font-semibold text-blue-600">{companySlug}</span></p>
        </div>

        {/* Content */}
        <div className="p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="p-4 rounded-lg border border-blue-100 bg-blue-50">
              <div className="text-xs uppercase tracking-wider text-blue-500 font-semibold mb-1">Server Tier</div>
              <div className="text-lg font-bold text-gray-800">Standard (t3.medium)</div>
            </div>
            <div className="p-4 rounded-lg border border-purple-100 bg-purple-50">
              <div className="text-xs uppercase tracking-wider text-purple-500 font-semibold mb-1">Current Status</div>
              <div className="text-lg font-bold text-gray-800">{project?.status.replace('_', ' ')}</div>
            </div>
          </div>

          <p className="text-gray-600 mb-8">
            Clicking the button below will trigger the Temporal Workflow to provision EC2, configure Docker, and install ERPNext v15.
          </p>

          <button
            onClick={handleDeploy}
            disabled={deploying}
            className={`w-full py-4 rounded-xl font-bold text-lg text-white shadow-lg transition-all 
              ${deploying 
                ? "bg-gray-400 cursor-not-allowed" 
                : "bg-black hover:bg-gray-900 hover:shadow-xl active:scale-[0.99]"
              }`}
          >
            {deploying ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Contacting Agents...
              </span>
            ) : (
              "🚀 Launch Infrastructure"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}