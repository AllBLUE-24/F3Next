"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { getBaseApiUrl } from "@/lib/config";

// Define the shape of the data based on your Temporal workflow output
interface RecommendationData {
  recommended_erp: string;
  fit_score: number;
  headline?: string;
  reasoning?: string;
  price_plan: string;
  industry: string;
  f3iche: string;
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
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-6 text-center">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-8"></div>
        <h2 className="text-2xl font-semibold text-gray-800 animate-pulse">
          Analyzing your infrastructure...
        </h2>
        <p className="text-gray-500 mt-2 max-w-md">
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
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
        <h2 className="text-2xl font-bold text-red-600">Something went wrong.</h2>
        <p className="text-gray-600 mt-2">We couldn't generate your recommendation.</p>
        <button onClick={() => window.location.reload()} className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-md">
          Try Again
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // VIEW: READY STATE (The Big Reveal)
  // ---------------------------------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="text-center">
          <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">
            Discovery Complete
          </p>
          <h1 className="mt-2 text-4xl font-extrabold text-gray-900 sm:text-5xl">
            {recommendation.headline || "Your ERP Blueprint is Ready"}
          </h1>
        </div>

        {/* The Scorecard Card */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
          <div className="p-8 sm:p-10">
            <div className="flex flex-col md:flex-row items-center justify-between gap-8">
              
              {/* Left Column: Details */}
              <div className="flex-1 space-y-4 text-center md:text-left">
                <h3 className="text-2xl font-bold text-gray-900">
                  {recommendation.recommended_erp}
                </h3>
                <p className="text-lg text-gray-600 leading-relaxed">
                  {recommendation.reasoning || "Based on your unique requirements, this configuration provides the best balance of features and scalability."}
                </p>
                <div className="flex flex-wrap gap-2 justify-center md:justify-start pt-2">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                    {recommendation.industry}
                  </span>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    Plan: {recommendation.price_plan}
                  </span>
                </div>
              </div>

              {/* Right Column: Fit Score Circular Indicator */}
              <div className="flex flex-col items-center justify-center shrink-0">
                <div className="relative w-32 h-32 flex items-center justify-center rounded-full bg-blue-50 border-8 border-blue-500 shadow-inner">
                  <span className="text-3xl font-extrabold text-blue-700">
                    {recommendation.fit_score}%
                  </span>
                </div>
                <span className="mt-3 text-sm font-semibold text-gray-500 uppercase">
                  System Fit Score
                </span>
              </div>

            </div>
          </div>
          
          {/* Bottom Action Bar */}
          <div className="bg-gray-50 px-8 py-6 border-t border-gray-100 sm:flex sm:items-center sm:justify-between">
            <p className="text-sm text-gray-500 mb-4 sm:mb-0 text-center sm:text-left">
              Ready to modernize your operations?
            </p>
            <button 
              onClick={() => console.log("Redirect to Stripe/Checkout")}
              className="w-full sm:w-auto flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors shadow-sm"
            >
              Proceed to Setup
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}