"use client";

import { useState, useEffect } from "react";
import { getBaseApiUrl } from "@/lib/config";

interface MigrationClientProps {
  projectId: string;
  companySlug: string;
}

export default function MigrationClient({ projectId, companySlug }: MigrationClientProps) {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<"upload" | "analyzing" | "review" | "done">("upload");
  const [workflowId, setWorkflowId] = useState("");
  
  // Mapping State
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [confidence, setConfidence] = useState(0);

  // 1. Upload Logic
  const handleUpload = async () => {
    if (!file) return;
    setStep("analyzing");

    try {
      // A. Get Secure S3 URL
      // We use companySlug here purely for organizing the S3 Folder structure (readable names)
      const API_BASE = getBaseApiUrl();
      const urlRes = await fetch(`${API_BASE}/api/migration/get-upload-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          filename: file.name, 
          file_type: file.type, 
          company_slug: companySlug 
        }),
      });
      
      const { upload_url, file_key } = await urlRes.json();

      // B. Upload Directly to S3
      await fetch(upload_url, { 
        method: "PUT", 
        body: file, 
        headers: { "Content-Type": file.type } 
      });

      // C. Start Workflow
      // CRITICAL: We send projectId here so the backend knows which DB entry to update
      const startRes = await fetch(`${API_BASE}/api/migration/start-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          file_key: file_key, 
          project_id: projectId, // <--- Using the resolved ID
          company_slug: companySlug 
        }),
      });

      const startData = await startRes.json();
      setWorkflowId(startData.workflow_id);

    } catch (error) {
      console.error(error);
      alert("Upload failed. Check console.");
      setStep("upload");
    }
  };

  // 2. Poll for AI Results
  useEffect(() => {
    if (step !== "analyzing" || !workflowId) return;

    const interval = setInterval(async () => {
      try {
        const API_BASE = getBaseApiUrl();
        const res = await fetch(`${API_BASE}/api/migration/status/${workflowId}`);
        const data = await res.json();

        if (data.status === "ready_for_review" && data.proposal) {
          setMapping(data.proposal.mappings);
          setConfidence(data.proposal.confidence);
          setStep("review");
          clearInterval(interval);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [step, workflowId]);

  // 3. Confirm Logic
  const handleConfirm = async () => {
    const API_BASE = getBaseApiUrl();
    await fetch(`${API_BASE}/api/migration/confirm-mapping`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workflow_id: workflowId,
        approved_mapping: mapping,
        project_id: projectId // <--- Ensuring consistency
      }),
    });
    setStep("done");
  };

  const updateMapping = (sourceCol: string, newVal: string) => {
    setMapping((prev) => ({ ...prev, [sourceCol]: newVal }));
  };

  return (
    <div className="p-8 max-w-4xl mx-auto fade-in-up">
      <h1 className="text-2xl font-bold text-white mb-8">Legacy Data Migration</h1>

      {/* STEP 1: UPLOAD */}
      {step === "upload" && (
        <div className="border-2 border-dashed border-[var(--border-default)] p-12 text-center rounded-2xl bg-[var(--bg-card)] hover:border-[var(--border-strong)] transition-colors">
          <input 
            type="file" 
            onChange={(e) => setFile(e.target.files?.[0] || null)} 
            className="block w-full text-sm text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-amber-500/10 file:text-amber-400 hover:file:bg-amber-500/20 file:transition-colors"
          />
          <button
            onClick={handleUpload}
            disabled={!file}
            className="mt-6 bg-amber-500 text-black px-8 py-3 rounded-xl font-bold hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Start Analysis
          </button>
        </div>
      )}

      {/* STEP 2: ANALYZING */}
      {step === "analyzing" && (
        <div className="text-center p-10">
          <div className="relative w-12 h-12 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full border-2 border-amber-500/20" />
            <div className="absolute inset-0 rounded-full border-2 border-amber-500 border-t-transparent animate-spin" />
          </div>
          <h2 className="text-lg font-bold text-white">AI is analyzing your file...</h2>
          <p className="text-zinc-500 text-sm mt-2">
            Connected to Project: <span className="font-mono bg-[var(--bg-elevated)] px-2 py-0.5 rounded text-zinc-300 text-xs">{projectId.split('-')[0]}...</span>
          </p>
        </div>
      )}

      {/* STEP 3: REVIEW UI */}
      {step === "review" && (
        <div className="surface-card overflow-hidden" style={{ borderRadius: 'var(--radius-lg)' }}>
          <div className="p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-white">Review Field Mapping</h2>
              <span className="bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-bold px-3 py-1 rounded-lg">
                Confidence: {(confidence * 100).toFixed(0)}%
              </span>
            </div>

            <div className="overflow-x-auto rounded-xl border border-[var(--border-subtle)]">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="bg-[var(--bg-elevated)]">
                    <th className="px-5 py-3 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">File Column</th>
                    <th className="px-5 py-3 text-[11px] font-bold text-zinc-500 uppercase tracking-wider">ERPNext Field</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(mapping).map(([sourceKey, targetVal]) => (
                    <tr key={sourceKey} className="border-t border-[var(--border-subtle)] hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-3 font-medium text-zinc-300 font-mono text-xs">{sourceKey}</td>
                      <td className="px-5 py-3">
                        <input
                          type="text"
                          value={targetVal || ""}
                          onChange={(e) => updateMapping(sourceKey, e.target.value)}
                          className="bg-[var(--bg-void)] border border-[var(--border-default)] text-zinc-200 text-sm rounded-lg focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/50 block w-full p-2 transition-all outline-none"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="px-6 py-4 border-t border-[var(--border-subtle)] bg-[var(--bg-shell)]">
            <button
              onClick={handleConfirm}
              className="w-full bg-green-500 hover:bg-green-400 text-black font-bold py-3 rounded-xl transition-colors"
            >
              Confirm & Import
            </button>
          </div>
        </div>
      )}

      {/* STEP 4: DONE */}
      {step === "done" && (
        <div className="p-8 bg-green-500/10 border border-green-500/20 text-green-400 rounded-2xl text-center">
          <h2 className="text-xl font-bold mb-2">Migration Queued! 🎉</h2>
          <p className="text-green-500/70 text-sm">The system is now transforming and importing your data.</p>
        </div>
      )}
    </div>
  );
}