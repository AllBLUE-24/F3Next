"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { useParams, useRouter } from "next/navigation";
import { 
  resolveProjectSlug, 
  getConfigStatus, 
  submitConfigAnswers,
  ConfigStatusResponse 
} from "@/lib/api/hooks_api"; 

export default function ConfigPage() {
  const params = useParams();
  const router = useRouter();
  
  // Safe Type Casting
  const companySlug = typeof params.companySlug === 'string' ? params.companySlug : '';
  const userSlug = typeof params.userSlug === 'string' ? params.userSlug : '';

  // --- STATE ---
  const [projectId, setProjectId] = useState<string | null>(null);
  const [containerId, setContainerId] = useState<string | null>(null);
  
  const [state, setState] = useState<ConfigStatusResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  
  // Phase: 'config' (answering) -> 'deploying' (agents running)
  const [isDeploying, setIsDeploying] = useState(false);

// 1. RESOLVE PROJECT (Inside ConfigPage component)
useEffect(() => {
  async function init() {
    if (!companySlug) return;
    try {
      const data = await resolveProjectSlug(companySlug); 
      console.log("✅ Resolved Project:", data);
      
      setProjectId(data.project_id);
      
      // 🔴 CRITICAL FIX: resolver.py doesn't return container_id
      // We MUST set this here so the button isn't blocked by (!containerId)
      setContainerId(data.container_id || "cnt_stock_109"); 
    } catch (err) {
      console.error("Project resolve failed", err);
    }
  }
  init();
}, [companySlug]);

  // 2. POLL STATUS & HANDLE AUTOMATIC HANDOFF
  useEffect(() => {
    // Stop polling if we haven't loaded IDs or if we are already deploying
    if (!containerId || isDeploying) return;
    
    const interval = setInterval(async () => {
      try {
        const data = await getConfigStatus(containerId);

        // 🔴 AUTO-START LOGIC
      if (data.status === "NOT_STARTED") {
        console.log("🚀 Workflow not running. Starting it now...");
        await axios.post("http://localhost:8000/api/config/start", {
          project_id: projectId,
          container_id: containerId,
          initial_tags: [] // Match the StartPayload structure
        });
        return; // Let the next poll cycle fetch the real state
      }

        setState(data);

        // 🟢 TRIGGER HANDOFF
        // Condition: Status is COMPLETED and we haven't started deploying yet
        if (data.status === "COMPLETED" && projectId && !isDeploying) {
          clearInterval(interval);
          setIsDeploying(true); // Stop double triggers
          console.log("✅ Config Complete. Triggering Deployment...");
          
          try {
            // 1. Tell Backend to Start Next Agents
            await axios.post("http://localhost:8000/api/deploy/start", {
              project_id: projectId,
              container_id: containerId
            });

            // 2. Redirect User to Template Page (Give user 2s to see success message)
            setTimeout(() => {
               router.push(`/${companySlug}/${userSlug}/templates`); 
            }, 2000);
            
          } catch (err) {
            console.error("Failed to trigger deployment", err);
            setIsDeploying(false); // Reset to retry on next poll if failed
          }
        }
      } catch (err) {
        // ignore polling errors
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [containerId, projectId, isDeploying, companySlug, userSlug, router]);

  // 3. SUBMIT ANSWERS
  const submitLayer = async () => {
    if (!containerId || !projectId) return;
    try {
      await submitConfigAnswers({
        container_id: containerId,
        project_id: projectId,
        answers: answers,
      });
      setAnswers({});
      // UI update handled by next poll
    } catch (err) {
      alert("Failed to submit");
    }
  };

  // --- VIEW 1: REDIRECTING / DEPLOYING ---
  if (isDeploying) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-white">
        <div className="mb-6 animate-bounce text-6xl">🚀</div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Configuration Complete!</h1>
        <p className="text-gray-500 mb-8">Launching System Builders & Generating Templates...</p>
        
        <div className="flex gap-4">
             <div className="flex items-center space-x-2 bg-blue-50 px-4 py-2 rounded-full border border-blue-100">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
                <span className="text-sm text-blue-800 font-medium">Applying Settings</span>
             </div>
             <div className="flex items-center space-x-2 bg-green-50 px-4 py-2 rounded-full border border-green-100">
                <div className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></div>
                <span className="text-sm text-green-800 font-medium">Generating CSVs</span>
             </div>
        </div>
      </div>
    );
  }

// --- VIEW 2: START OR LOADING ---
if (!state) {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gray-50">
      {!projectId ? (
        <div className="animate-pulse text-gray-400">Resolving Project Context...</div>
      ) : (
        <div className="text-center bg-white p-10 rounded-2xl shadow-xl border max-w-md">
          <div className="text-5xl mb-6">🛠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Ready to Configure</h2>
          <p className="text-gray-500 mb-8">
            We've resolved your project. Click below to wake up the Configuration Agent and begin tailoring your ERP.
          </p>
          <button 
          // Inside your button's onClick handler in page.tsx
          onClick={async () => {
            // 1. Safety Check: If IDs aren't ready, don't even try the call
            if (!projectId || !containerId) {
              alert("Project context not yet resolved. Please wait a second.");
              return;
            }
          
            try {
              console.log("🚀 Manual Start Triggered with:", { projectId, containerId });
              
              // 2. Explicitly construct the payload to ensure no keys are missing
              const payload = {
                project_id: projectId,     // Must be a valid UUID string
                container_id: containerId, // e.g., "cnt_stock_109"
                initial_tags: []           // 🔴 Required by Pydantic StartPayload
              };
          
              const response = await axios.post("http://localhost:8000/api/config/start", payload);
              
              console.log("✅ Agent Started:", response.data);
            } catch (err: any) {
              // 3. Log the ACTUAL validation error from FastAPI
              if (err.response?.status === 422) {
                console.error("❌ Validation Error Details:", err.response.data.detail);
                alert("Backend rejected the data format. Check console for details.");
              } else {
                console.error("❌ System Error:", err);
                alert("Failed to start agent. Ensure Backend and Worker are running.");
              }
            }
          }}
        
          className="w-full py-4 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-all shadow-lg active:scale-95"
          >
            Start Configuration Agent
          </button>
        </div>
      )}
    </div>
  );
}
const visibleQuestions = state?.questions ? state.questions.filter(q => q.ui_type !== 'hidden') : [];
  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
       <div className="mb-8 flex items-center justify-between border-b pb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">System Configuration</h1>
            <p className="text-sm text-gray-500 mt-1">Tailoring ERPNext for {companySlug}</p>
          </div>
          <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-xs font-mono uppercase">
            {state.status}
          </span>
      </div>
      
       <div className="space-y-6">
        {visibleQuestions.map((q) => (
          <div key={q.node_id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="font-semibold text-lg text-gray-800 mb-4">{q.question}</h3>
            <div className="space-y-3">
              {q.options.map((opt: any) => {
                const isSelected = String(answers[q.node_id]) === String(opt.value);
                return (
                  <label key={String(opt.value)} className={`flex items-center p-4 rounded-lg border cursor-pointer transition-all ${isSelected ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' : 'hover:bg-gray-50 border-gray-200'}`}>
                    <input 
                        type="radio" 
                        name={q.node_id} 
                        value={String(opt.value)} 
                        checked={isSelected} 
                        onChange={() => setAnswers(prev => ({ ...prev, [q.node_id]: opt.value }))} 
                        className="h-5 w-5 text-blue-600 border-gray-300 focus:ring-blue-500" 
                    />
                    <span className="ml-3 text-base font-medium text-gray-900">{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
        ))}
        
        {visibleQuestions.length > 0 && (
            <button 
                onClick={submitLayer} 
                className="w-full py-4 bg-gray-900 text-white rounded-xl font-bold hover:bg-black transition-transform active:scale-[0.99] shadow-lg"
            >
            Confirm & Continue →
            </button>
        )}
      </div>
    </div>
  );
}