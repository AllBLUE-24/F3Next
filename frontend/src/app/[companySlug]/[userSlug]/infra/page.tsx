"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useRouter } from "next/navigation";
import { getBaseApiUrl } from "@/lib/config";
import { Loader2, Rocket, Server, Activity, ExternalLink, Copy } from "lucide-react";

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
        const apiUrl = getBaseApiUrl();
        const res = await axios.get(`${apiUrl}/api/resolve/slug/${companySlug}`);
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
      const apiUrl = getBaseApiUrl();
      await axios.post(`${apiUrl}/api/deploy/infra`, {
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
      <div className="flex min-h-[60vh] items-center justify-center fade-in-up">
        <div className="flex items-center gap-3 text-zinc-500">
          <Loader2 className="w-5 h-5 animate-spin text-amber-500" />
          <span className="text-sm font-medium">Resolving Context...</span>
        </div>
      </div>
    );
  }

  if (error && !project) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center fade-in-up">
        <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-5">
          <span className="text-2xl">⚠️</span>
        </div>
        <h1 className="text-lg font-bold text-white mb-1">{error}</h1>
        <p className="text-zinc-500 text-sm">Check the backend connection and try again.</p>
      </div>
    );
  }

  // State for deployment details
  const [deploymentInfo, setDeploymentInfo] = useState<any>(null);

  // Poll deployment status after successful trigger
  useEffect(() => {
    if (!deploySuccess) return;
    const interval = setInterval(async () => {
      try {
        const apiUrl = getBaseApiUrl();
        const res = await axios.get(`${apiUrl}/api/deployment/${project?.project_id}`);
        if (res.data.status === 'ready') {
          setDeploymentInfo(res.data);
          clearInterval(interval);
        }
      } catch (e) {
        console.error('Error fetching deployment state', e);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [deploySuccess, project?.project_id]);

  return (
    <div className="max-w-3xl mx-auto py-8 fade-in-up">
      <div className="surface-card overflow-hidden" style={{ borderRadius: 'var(--radius-xl)' }}>
        
        {/* Header */}
        <div className="bg-[var(--bg-shell)] px-7 py-5 border-b border-[var(--border-subtle)]">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/25 flex items-center justify-center">
              <Rocket className="w-4 h-4 text-amber-400" />
            </div>
            <h1 className="text-lg font-bold text-white">Infrastructure Launchpad</h1>
          </div>
          <p className="text-xs text-zinc-500 ml-11">
            Deploy ERPNext for <span className="font-semibold text-amber-400">{companySlug}</span>
          </p>
        </div>

        {/* Content */}
        <div className="p-7">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)]">
              <div className="flex items-center gap-2 mb-1.5">
                <Server className="w-3.5 h-3.5 text-zinc-500" />
                <span className="text-[10px] uppercase tracking-wider text-zinc-600 font-bold">Server Tier</span>
              </div>
              <div className="text-sm font-bold text-white">Standard (t3.medium)</div>
            </div>
            <div className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)]">
              <div className="flex items-center gap-2 mb-1.5">
                <Activity className="w-3.5 h-3.5 text-zinc-500" />
                <span className="text-[10px] uppercase tracking-wider text-zinc-600 font-bold">Current Status</span>
              </div>
              <div className="text-sm font-bold text-white capitalize">{project?.status.replace('_', ' ')}</div>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <p className="text-zinc-500 text-sm mb-6 leading-relaxed">
            Clicking the button below will provision EC2, configure Docker, and install ERPNext v15 via the Temporal workflow.
          </p>

          <button
            onClick={handleDeploy}
            disabled={deploying || deploySuccess}
            className={`w-full py-3.5 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2
              ${deploying || deploySuccess
                ? "bg-zinc-800 text-zinc-500 cursor-not-allowed border border-[var(--border-subtle)]" 
                : "bg-amber-500 text-black hover:bg-amber-400 shadow-lg shadow-amber-500/10 active:scale-[0.99]"
              }`}
          >
            {deploying ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Contacting Agents...
              </>
            ) : deploySuccess ? (
              "✓ Deployment Triggered"
            ) : (
              <>
                <Rocket className="w-4 h-4" />
                Launch Infrastructure
              </>
            )}
          </button>
        </div>

        {/* Deployment Details */}
        {deploymentInfo && (
          <div className="mx-7 mb-7 p-5 bg-green-500/8 rounded-xl border border-green-500/20">
            <h2 className="text-sm font-bold mb-4 text-green-400 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              Deployment Successful
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-zinc-500 text-xs font-medium w-24 flex-shrink-0">Site URL</span>
                <a href={deploymentInfo.instanceUrl} target="_blank" rel="noopener noreferrer" className="text-amber-400 hover:text-amber-300 underline underline-offset-2 flex items-center gap-1">
                  {deploymentInfo.instanceUrl}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-500 text-xs font-medium w-24 flex-shrink-0">User ID</span>
                <span className="font-mono bg-[var(--bg-void)] px-2 py-0.5 rounded text-zinc-300 text-xs border border-[var(--border-subtle)]">{deploymentInfo.userId || "Administrator"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-500 text-xs font-medium w-24 flex-shrink-0">Password</span>
                <span className="font-mono bg-[var(--bg-void)] px-2 py-0.5 rounded text-zinc-300 text-xs border border-[var(--border-subtle)] select-all">{deploymentInfo.adminPassword}</span>
              </div>
              {deploymentInfo.api_key && (
                <div className="flex items-center gap-2">
                  <span className="text-zinc-500 text-xs font-medium w-24 flex-shrink-0">API Key</span>
                  <span className="font-mono bg-[var(--bg-void)] px-2 py-0.5 rounded text-zinc-300 text-xs border border-[var(--border-subtle)] select-all">{deploymentInfo.api_key}</span>
                </div>
              )}
              {deploymentInfo.api_secret && (
                <div className="flex items-center gap-2">
                  <span className="text-zinc-500 text-xs font-medium w-24 flex-shrink-0">API Secret</span>
                  <span className="font-mono bg-[var(--bg-void)] px-2 py-0.5 rounded text-zinc-300 text-xs border border-[var(--border-subtle)] select-all">{deploymentInfo.api_secret}</span>
                </div>
              )}
              {deploymentInfo.container_id && (
                <div className="flex items-center gap-2">
                  <span className="text-zinc-500 text-xs font-medium w-24 flex-shrink-0">Container</span>
                  <span className="font-mono bg-[var(--bg-void)] px-2 py-0.5 rounded text-zinc-300 text-xs border border-[var(--border-subtle)] select-all">{deploymentInfo.container_id}</span>
                </div>
              )}
            </div>
            <p className="mt-4 text-xs text-green-500/70 font-medium">Save these credentials securely before proceeding.</p>
          </div>
        )}
      </div>
    </div>
  );
}