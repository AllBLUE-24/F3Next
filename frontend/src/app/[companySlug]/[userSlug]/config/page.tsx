"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { useParams } from "next/navigation";
import { 
  resolveProjectSlug, 
  getConfigStatus, 
  submitConfigAnswers,
  ConfigStatusResponse 
} from "@/lib/api/hooks_api"; // Importing your centralized hooks


// --- TYPES ---
interface Option {
  label: string;
  value: any;
  tags_injected?: string[];
}

interface Question {
  node_id: string;
  title: string;
  question: string;
  ui_type: "radio" | "boolean" | "hidden";
  options: Option[];
}

interface WorkflowState {
  status: string;
  layer: number;
  questions: Question[];
}

export default function ConfigPage() {
  const params = useParams();
  const companySlug = params.companySlug as string;

  // --- STATE ---
  const [projectId, setProjectId] = useState<string | null>(null); // <--- Storing Project ID
  const [containerId, setContainerId] = useState<string | null>(null);
  const [state, setState] = useState<ConfigStatusResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1. RESOLVE PROJECT
  useEffect(() => {
    async function init() {
      if (!companySlug) return;
      try {
        const data = await resolveProjectSlug(companySlug);
        setProjectId(data.project_id);
        
        // For this demo, we use the hardcoded container from resolver 
        // OR fallback to our test ID if the resolver doesn't return one yet
        setContainerId(data.container_id || "cnt_stock_109"); 
      } catch (err) {
        console.error(err);
        setError("Project not found.");
      }
    }
    init();
  }, [companySlug]);

  // 2. POLL STATUS
  useEffect(() => {
    if (!containerId) return;
    const interval = setInterval(async () => {
      try {
        const data = await getConfigStatus(containerId);
        setState(data);
      } catch (err) {
        // Workflow might not be running yet
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [containerId]);

  // 3. SUBMIT ANSWERS
  const submitLayer = async () => {
    if (!containerId || !projectId) return; // Guard clause
    setLoading(true);
    try {
      await submitConfigAnswers({
        container_id: containerId,
        project_id: projectId, // <--- PASSING IT DOWN HERE
        answers: answers,
      });
      setAnswers({});
    } catch (err) {
      alert("Failed to submit answers");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (nodeId: string, val: any) => {
    setAnswers((prev) => ({ ...prev, [nodeId]: val }));
  };


  // --- RENDER HELPERS ---
  if (error) return <div className="p-10 text-red-500">{error}</div>;
  if (!state) return <div className="p-10 text-gray-500">Connecting to F3Next Agent...</div>;

  if (state.status === "COMPLETED") {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-green-50">
        <h1 className="text-3xl font-bold text-green-700 mb-2">Configuration Complete!</h1>
        <p className="text-gray-600">Your ERPNext Inventory Module is ready.</p>
      </div>
    );
  }

  // Filter out hidden questions (e.g. Layer 4 cleanup)
  const visibleQuestions = state.questions ? state.questions.filter(q => q.ui_type !== 'hidden') : [];

  if (visibleQuestions.length === 0 && state.status.includes("WAITING")) {
    return <div className="p-10 text-blue-600 animate-pulse">Processing Rules...</div>;
  }

  if (state.status === "COMPLETED") {
    return <div className="p-10 text-green-600 font-bold">Configuration Complete!</div>;
  }

  
  // --- MAIN UI ---
return (
    <div className="max-w-3xl mx-auto py-12 px-6">
       {/* ... UI Code from previous turn ... */}
       <div className="mb-8 border-b pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Config Agent</h1>
        <div className="text-xs text-gray-400 font-mono mt-1">
            PID: {projectId} | CID: {containerId}
        </div>
      </div>
      
       <div className="space-y-8">
        {visibleQuestions.map((q) => (
          <div key={q.node_id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="font-semibold text-lg text-gray-800 mb-3">{q.question}</h3>
            <div className="space-y-3">
              {q.options.map((opt: any) => {
                const isSelected = String(answers[q.node_id]) === String(opt.value);
                return (
                  <label key={String(opt.value)} className={`flex items-center p-3 rounded-lg border cursor-pointer ${isSelected ? 'border-blue-500 bg-blue-50' : 'hover:bg-gray-50'}`}>
                    <input type="radio" name={q.node_id} value={String(opt.value)} checked={isSelected} onChange={() => handleAnswerChange(q.node_id, opt.value)} className="form-radio h-5 w-5 text-blue-600" />
                    <span className="ml-3 text-sm font-medium text-gray-900">{opt.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
        ))}
        <button onClick={submitLayer} disabled={loading} className="w-full py-4 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 disabled:bg-gray-400">
           {loading ? "Processing..." : "Next Step →"}
        </button>
      </div>
    </div>
  );
}