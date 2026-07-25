"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import WorkflowPreviewDisplay, {
  type WorkflowExplanation,
} from "@/components/discovery/WorkflowPreviewDisplay";
import {
  confirmDiscoveryModules,
  getWorkflowPreview,
} from "@/lib/api/hooks_api";
import { getBaseApiUrl } from "@/lib/config";

interface RecommendationData {
  f3iche: string;
  industry: string;
  price_plan: string;
  recommended_erp?: string;
  fit_score?: number;
  headline?: string;
  reasoning?: string;
  phase?: string;
  mvp_focus?: {
    primary_bottleneck: string;
    functional_requirements: string[];
  };
}

export default function RecommendationPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();

  const companySlug = params.companySlug as string;
  const userSlug = params.userSlug as string;
  const projectId = searchParams.get("projectId");

  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [recommendation, setRecommendation] = useState<RecommendationData | null>(null);
  const [phase, setPhase] = useState<string>("initial_chat");
  const [workflowPreview, setWorkflowPreview] = useState<{
    workflow_explanation: WorkflowExplanation;
    seed_doctypes: string[];
    deferred_doctypes?: string[];
    required_doctypes: string[];
    promoted_doctypes?: string[];
    dual_system_note?: string;
    assurance?: { level?: string; reasons?: string[]; requires_acknowledgment?: boolean };
    closure_test?: string;
    promotion_labels?: Record<string, string>;
    validator_warnings?: Array<{ message?: string; suggested_doctypes?: string[] }>;
    upload_schema_preview?: Record<string, unknown>;
  } | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);

  useEffect(() => {
    if (!projectId) {
      console.error("No projectId provided in URL");
      setStatus("error");
      return;
    }

    const checkStatus = async () => {
      try {
        const apiUrl = getBaseApiUrl();
        const res = await fetch(`${apiUrl}/api/discovery/${projectId}/recommendation`);

        if (!res.ok) throw new Error("Failed to fetch status");

        const json = await res.json();

        if (json.status === "ready" && json.data) {
          setRecommendation(json.data);
          setPhase(json.phase || json.data.phase || "initial_chat");
          setStatus("ready");

          const awaiting =
            json.awaiting_confirmation ||
            (json.phase &&
              json.phase !== "finalized" &&
              (json.data.workflow_explanation || json.data.target_structure));

          if (awaiting) {
            const data = json.data;
            const workflow = data.workflow_explanation;
            const target = data.target_structure || {};
            if (workflow && (target.seed_doctypes?.length || target.required_doctypes?.length)) {
              setWorkflowPreview({
                workflow_explanation: workflow as WorkflowExplanation,
                seed_doctypes: target.seed_doctypes || [],
                deferred_doctypes: target.deferred_doctypes || [],
                required_doctypes: target.required_doctypes || [],
                promoted_doctypes: target.promoted_doctypes || data.promoted_doctypes || [],
                dual_system_note: target.dual_system_note,
                assurance: data.assurance || json.data?.discovery_metadata?.assurance,
                closure_test: data.closure_test || json.data?.discovery_metadata?.closure_test,
                promotion_labels:
                  data.promotion_labels || json.data?.discovery_metadata?.promotion_labels,
                validator_warnings:
                  data.validator_warnings || json.data?.discovery_metadata?.validator_warnings,
                upload_schema_preview:
                  data.upload_schema_preview || json.data?.discovery_metadata?.upload_schema_preview,
              });
            } else {
              try {
                const preview = await getWorkflowPreview(projectId);
                setWorkflowPreview({
                  workflow_explanation: preview.workflow_explanation as WorkflowExplanation,
                  seed_doctypes: preview.seed_doctypes,
                  deferred_doctypes: preview.deferred_doctypes,
                  required_doctypes: preview.required_doctypes,
                  promoted_doctypes: preview.promoted_doctypes,
                  dual_system_note: preview.dual_system_note ?? preview.discovery_metadata?.target_structure?.dual_system_note,
                  assurance: preview.assurance,
                  closure_test: preview.closure_test,
                  promotion_labels: preview.promotion_labels,
                  validator_warnings: preview.validator_warnings,
                  upload_schema_preview: preview.upload_schema_preview,
                });
              } catch (previewErr) {
                console.warn("Workflow preview load failed:", previewErr);
              }
            }
          }
        }
      } catch (error) {
        console.error("Polling error:", error);
      }
    };

    let interval: NodeJS.Timeout;
    if (status === "loading") {
      checkStatus();
      interval = setInterval(checkStatus, 3000);
    }

    return () => clearInterval(interval);
  }, [status, projectId, companySlug, userSlug]);

  // ---------------------------------------------------------------------------
  // VIEW: LOADING STATE
  // ---------------------------------------------------------------------------
  if (status === "loading") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] p-6 text-center fade-in-up">
        <div className="relative w-16 h-16 mb-8">
          <div className="absolute inset-0 rounded-full border-2 border-amber-500/20" />
          <div className="absolute inset-0 rounded-full border-2 border-amber-500 border-t-transparent animate-spin" />
          <div className="absolute inset-3 rounded-full bg-amber-500/10 flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          </div>
        </div>
        <h2 className="text-xl font-bold text-white mb-2">
          Analyzing your infrastructure...
        </h2>
        <p className="text-zinc-500 text-sm max-w-md leading-relaxed">
          Our AI architect is matching your operational tags to the best ERPNext configuration. This usually takes about 10-15 seconds.
        </p>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // VIEW: ERROR STATE
  // ---------------------------------------------------------------------------
  if (status === "error" || !recommendation) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] text-center fade-in-up">
        <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6">
          <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Something went wrong.</h2>
        <p className="text-zinc-500 text-sm mb-6">We couldn&apos;t generate your recommendation.</p>
        <button 
          onClick={() => window.location.reload()} 
          className="px-5 py-2.5 bg-white/[0.06] hover:bg-white/[0.1] border border-[var(--border-default)] text-white text-sm font-medium rounded-xl transition-all"
        >
          Try Again
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Fit Score Ring
  // ---------------------------------------------------------------------------
  const score = recommendation.fit_score || 85; // Default if not yet computed
  const circumference = 2 * Math.PI * 52;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Format F3iche for display
  const formatF3iche = (f3iche: string) => {
    const mapping: Record<string, string> = {
      "manufacturing": "Manufacturing",
      "process_mfg_batch": "Process Manufacturing (Batch)",
      "discrete_mfg": "Discrete Manufacturing",
      "trading": "Trading & Distribution",
      "service": "Service",
      "retail": "Retail",
    };
    return mapping[f3iche] || f3iche.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  const handleConfirmModules = async (adjustments: {
    confirmed_doctypes: string[];
    added_doctypes: string[];
    removed_doctypes: string[];
    notes: string;
  }) => {
    if (!projectId) return;
    setIsConfirming(true);
    try {
      await confirmDiscoveryModules({
        project_id: projectId,
        ...adjustments,
      });
      setPhase("finalized");
      setWorkflowPreview(null);
    } catch (error) {
      console.error("Confirm modules error:", error);
      alert(error instanceof Error ? error.message : "Could not save workflow confirmation.");
    } finally {
      setIsConfirming(false);
    }
  };

  const handleProceedToImplementation = async () => {
    if (!projectId) return;
    
    setIsGenerating(true);
    
    try {
      const apiUrl = getBaseApiUrl();
      const response = await fetch(
        `${apiUrl}/api/discovery/${projectId}/proceed-to-implementation`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to generate target structure");
      }
      
      const result = await response.json();
      console.log("✅ Target structure generated:", result);
      
      // Navigate to upload page
      router.push(`/${companySlug}/${userSlug}/upload?projectId=${projectId}`);
      
    } catch (error) {
      console.error("❌ Error generating target structure:", error);
      alert("Failed to generate target structure. Please try again.");
      setIsGenerating(false);
    }
  };

  const awaitingConfirmation =
    phase !== "finalized" && workflowPreview !== null;

  if (awaitingConfirmation && workflowPreview) {
    return (
      <div className="max-w-3xl mx-auto space-y-6 fade-in-up">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/20 bg-amber-500/8 px-3 py-1">
            <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">
              Step 1 — Discovery Assistant
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Confirm your implementation plan
          </h1>
          <p className="text-zinc-500 text-sm max-w-lg mx-auto">
            Review the workflow and data we need before you upload files.
          </p>
        </div>
        <WorkflowPreviewDisplay
          preview={workflowPreview}
          onConfirm={handleConfirmModules}
          isSubmitting={isConfirming}
        />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // VIEW: READY STATE (The Big Reveal)
  // ---------------------------------------------------------------------------
  return (
    <div className="max-w-3xl mx-auto space-y-8 fade-in-up">
      
      {/* Header Section */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/20 bg-amber-500/8 px-3 py-1">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">
            {phase === "finalized" ? "Blueprint Confirmed" : "Discovery Complete"}
          </span>
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
          {recommendation.headline || "Your ERP Blueprint is Ready"}
        </h1>
      </div>

      {/* The Scorecard Card */}
      <div className="surface-card overflow-hidden" style={{ borderRadius: 'var(--radius-xl)' }}>
        <div className="p-8 sm:p-10">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            
            {/* Left Column: Details */}
            <div className="flex-1 space-y-4 text-center md:text-left">
              <h3 className="text-2xl font-bold text-white">
                {recommendation.recommended_erp || `ERPNext for ${formatF3iche(recommendation.f3iche)}`}
              </h3>
              <p className="text-zinc-400 text-sm leading-relaxed">
                {recommendation.reasoning || `Tailored configuration for ${formatF3iche(recommendation.f3iche)} businesses in ${recommendation.industry}.`}
              </p>
              {recommendation.mvp_focus && (
                <div className="text-zinc-500 text-xs leading-relaxed pt-3 border-t border-zinc-800 space-y-2">
                  {recommendation.mvp_focus.primary_bottleneck && (
                    <div>
                      <span className="font-semibold text-zinc-400">Primary Focus:</span>{" "}
                      {recommendation.mvp_focus.primary_bottleneck}
                    </div>
                  )}
                  {recommendation.mvp_focus.functional_requirements?.length > 0 && (
                    <div>
                      <span className="font-semibold text-zinc-400">Key Requirements:</span>
                      <ul className="list-disc list-inside mt-1 space-y-0.5 pl-2">
                        {recommendation.mvp_focus.functional_requirements.map((req, idx) => (
                          <li key={idx}>{req}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              <div className="flex flex-wrap gap-2 justify-center md:justify-start pt-2">
                <span className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-semibold bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  {formatF3iche(recommendation.f3iche)}
                </span>
                <span className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-semibold bg-blue-500/10 border border-blue-500/20 text-blue-400">
                  {recommendation.industry}
                </span>
                <span className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-semibold bg-green-500/10 border border-green-500/20 text-green-400">
                  Plan: {recommendation.price_plan}
                </span>
              </div>
            </div>

            {/* Right Column: Fit Score — SVG ring */}
            <div className="flex flex-col items-center justify-center shrink-0">
              <div className="relative w-32 h-32">
                <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
                  {/* Track */}
                  <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
                  {/* Progress */}
                  <circle
                    cx="60" cy="60" r="52" fill="none"
                    stroke="#f59e0b"
                    strokeWidth="6"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    style={{ transition: 'stroke-dashoffset 1s ease-out' }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold text-white">
                    {score}%
                  </span>
                </div>
              </div>
              <span className="mt-3 text-[10px] font-bold text-zinc-600 uppercase tracking-wider">
                System Fit Score
              </span>
            </div>

          </div>
        </div>
        
        {/* Bottom Action Bar */}
        <div className="px-8 py-5 border-t border-[var(--border-subtle)] bg-[var(--bg-shell)] sm:flex sm:items-center sm:justify-between">
          <p className="text-xs text-zinc-600 mb-4 sm:mb-0 text-center sm:text-left">
            {isGenerating
              ? "Preparing upload..."
              : phase !== "finalized"
                ? "Confirm workflow above before uploading"
                : "Ready to upload your data?"}
          </p>
          <button 
            onClick={handleProceedToImplementation}
            disabled={isGenerating || phase !== "finalized"}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-amber-500/50 disabled:cursor-not-allowed text-black text-sm font-bold rounded-xl transition-colors shadow-lg shadow-amber-500/10"
          >
            {isGenerating ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Generating Blueprint...
              </>
            ) : (
              <>
                Proceed to Upload
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </>
            )}
          </button>
        </div>
      </div>

    </div>
  );
}