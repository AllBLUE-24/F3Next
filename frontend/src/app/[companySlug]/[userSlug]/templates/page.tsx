"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import axios from "axios";

export default function TemplatesPage() {
  const params = useParams();
  const companySlug = params.companySlug as string;
  
  const [status, setStatus] = useState("generating"); // 'generating' | 'ready'
  const [templateUrls, setTemplateUrls] = useState<any>(null);

  // Poll for Template Readiness
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        // You need an endpoint to check project status or template workflow status
        // For now, let's assume an endpoint that returns the project details
        const res = await axios.get(`http://localhost:8000/api/project/slug/${companySlug}`);
        const project = res.data;

        // Check if templates are ready (You'll update this enum in DB when Template Agent finishes)
        if (project.status === "templates_ready" || project.status === "deployment_in_progress") {
           // If your Template Agent saves URLs to DB, fetch them here
           // For demo, we can just show buttons if status allows
           setStatus("ready");
           // setTemplateUrls(project.template_urls); 
           clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [companySlug]);

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Data Import</h1>
        <p className="text-gray-600 mt-2">Download the customized templates, fill them with your legacy data, and upload them here.</p>
      </div>

      {status === "generating" ? (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-8 text-center">
            <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
            <h3 className="text-lg font-semibold text-blue-800">Generating Custom Templates...</h3>
            <p className="text-blue-600 text-sm mt-2">Our agents are building CSVs based on your configuration.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Download Section */}
            <div className="bg-white p-6 rounded-xl border shadow-sm">
                <h3 className="font-bold text-lg mb-4">1. Download Templates</h3>
                <div className="space-y-3">
                    <button className="w-full flex items-center justify-between p-3 border rounded hover:bg-gray-50">
                        <span>📦 Item Master Template.csv</span>
                        <span className="text-blue-600 font-medium">Download</span>
                    </button>
                    <button className="w-full flex items-center justify-between p-3 border rounded hover:bg-gray-50">
                        <span>🏭 Warehouse Tree.csv</span>
                        <span className="text-blue-600 font-medium">Download</span>
                    </button>
                </div>
            </div>

            {/* Upload Section */}
            <div className="bg-white p-6 rounded-xl border shadow-sm">
                <h3 className="font-bold text-lg mb-4">2. Upload Data</h3>
                <div className="border-2 border-dashed border-gray-300 rounded-lg h-40 flex flex-col items-center justify-center text-gray-500 hover:border-blue-500 hover:bg-blue-50 transition">
                    <span>Drag & Drop filled CSVs here</span>
                    <button className="mt-2 px-4 py-2 bg-gray-900 text-white text-sm rounded">Select Files</button>
                </div>
            </div>
        </div>
      )}
    </div>
  );
}