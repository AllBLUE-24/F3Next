"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { getBaseApiUrl } from "@/lib/config";

// Define the shape of discovery_metadata from backend
interface RecommendationData {
  f3iche: string;
  industry: string;
  price_plan: string;
  recommended_erp?: string;
  fit_score?: number;
  headline?: string;
  reasoning?: string;
  mvp_focus?: {
    primary_bottleneck: string;
    functional_requirements: string[];
  };
}

export default function RecommendationPage() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams(); // Grab query parameters
    
    const companySlug = params.companySlug as string;
    const userSlug = params.userSlug as string;
    const projectId = searchParams.get("projectId"); // Extract the ID
  
    const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
    const [recommendation, setRecommendation] = useState<RecommendationData | null>(null);
  
    useEffect(() => {
      // Stop if we don't have a projectId
      if (!projectId) {
        console.error("No projectId provided in URL");
        setStatus("error");
        return;
      }
  
      const checkStatus = async () => {
        try {
          const apiUrl = getBaseApiUrl();
          // UPDATE THIS LINE: Pointing to your discovery.py endpoint
          const res = await fetch(`${apiUrl}/api/discovery/${projectId}/recommendation`);
          
          if (!res.ok) throw new Error("Failed to fetch status");
        
        const json = await res.json();

        if (json.status === "ready" && json.data) {
          setRecommendation(json.data);
          setStatus("ready");
        }
      } catch (error) {
        console.error("Polling error:", error);
        // Optional: setStatus("error") if you want to abort on first failure
      }
    };

    // If we are still loading, poll every 3 seconds
    let interval: NodeJS.Timeout;
    if (status === "loading") {
      checkStatus(); // Check immediately once
      interval = setInterval(checkStatus, 3000);
    }

    // Cleanup interval on unmount or when status changes
    return () => clearInterval(interval);
  }, [status, companySlug, userSlug]);

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
            Discovery Complete
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
            Ready to modernize your operations?
          </p>
          <button 
            onClick={() => router.push(`/${companySlug}/${userSlug}/upload`)}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-black text-sm font-bold rounded-xl transition-colors shadow-lg shadow-amber-500/10"
          >
            Proceed to Implementation
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </button>
        </div>
      </div>

    </div>
  );
}