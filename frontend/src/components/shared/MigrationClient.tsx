"use client";

import { useState, useEffect } from "react";

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
      const API_BASE = (typeof window !== "undefined" ? "" : "http://backend_api:8000");
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
        const API_BASE = (typeof window !== "undefined" ? "" : "http://backend_api:8000");
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
    const API_BASE = (typeof window !== "undefined" ? "" : "http://backend_api:8000");
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
    <div className="p-10 max-w-4xl mx-auto font-sans text-gray-800">
      <h1 className="text-3xl font-bold mb-8">Legacy Data Migration</h1>

      {/* STEP 1: UPLOAD */}
      {step === "upload" && (
        <div className="border-2 border-dashed border-gray-300 p-12 text-center rounded-xl bg-white">
          <input 
            type="file" 
            onChange={(e) => setFile(e.target.files?.[0] || null)} 
            className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <button
            onClick={handleUpload}
            disabled={!file}
            className="mt-6 bg-black text-white px-8 py-3 rounded-lg hover:bg-gray-800 disabled:opacity-50"
          >
            Start Analysis
          </button>
        </div>
      )}

      {/* STEP 2: ANALYZING */}
      {step === "analyzing" && (
        <div className="text-center p-10">
          <div className="animate-spin text-4xl mb-4">⚙️</div>
          <h2 className="text-xl font-semibold">AI is analyzing your file...</h2>
          <p className="text-gray-500 mt-2">Connecting to Project: <span className="font-mono bg-gray-200 px-1">{projectId.split('-')[0]}...</span></p>
        </div>
      )}

      {/* STEP 3: REVIEW UI */}
      {step === "review" && (
        <div className="bg-white shadow-lg rounded-lg p-6 border border-gray-200">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">Review Field Mapping</h2>
            <span className="bg-blue-100 text-blue-800 text-sm font-medium px-3 py-1 rounded">
              Confidence: {(confidence * 100).toFixed(0)}%
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-gray-500">
              <thead className="text-xs text-gray-700 uppercase bg-gray-100">
                <tr>
                  <th className="px-6 py-3">File Column</th>
                  <th className="px-6 py-3">ERPNext Field</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(mapping).map(([sourceKey, targetVal]) => (
                  <tr key={sourceKey} className="bg-white border-b">
                    <td className="px-6 py-4 font-medium text-gray-900">{sourceKey}</td>
                    <td className="px-6 py-4">
                      <input
                        type="text"
                        value={targetVal || ""}
                        onChange={(e) => updateMapping(sourceKey, e.target.value)}
                        className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={handleConfirm}
            className="mt-6 w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg"
          >
            Confirm & Import
          </button>
        </div>
      )}

      {/* STEP 4: DONE */}
      {step === "done" && (
        <div className="p-6 bg-green-50 text-green-800 rounded-lg text-center border border-green-200">
          <h2 className="text-2xl font-bold mb-2">Migration Queued! 🎉</h2>
          <p>The system is now transforming and importing your data.</p>
        </div>
      )}
    </div>
  );
}