"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import {
  Upload,
  File as FileIcon,
  CheckCircle,
  XCircle,
  Loader2,
} from "lucide-react";

export default function IngestionPage() {
  const params = useParams();
  const companyslug = params.companySlug as string;
  const userslug = params.userSlug as string;

  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleUpload = async () => {
    if (!files.length) return;

    setLoading(true);
    setStatus("idle");
    setMessage("");

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));

      const res = await fetch("http://localhost:8000/api/ingest", {
        method: "POST",
        headers: {
          "x-company-slug": companyslug,
          "x-user-slug": userslug,
        },
        body: formData,
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || "Upload failed");
      }

      const data = await res.json();
      setStatus("success");
      setMessage(
        `${data.count} file(s) uploaded for client "${companyslug}"`
      );
      setFiles([]);
    } catch (err: any) {
      setStatus("error");
      setMessage(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 flex items-center justify-center px-6">
      <div className="w-full max-w-xl rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl p-8">
        {/* Header */}
        <h1 className="text-2xl font-semibold text-white text-center">
          Client File Ingestion
        </h1>
        <p className="text-sm text-slate-400 text-center mt-2">
          Client: <span className="text-slate-200">{companyslug}</span> · User:{" "}
          <span className="text-slate-200">{userslug}</span>
        </p>

        {/* Upload Area */}
        <label className="mt-8 flex flex-col items-center justify-center gap-4 border-2 border-dashed border-white/20 rounded-xl p-8 cursor-pointer hover:border-blue-400 transition">
          <Upload className="w-10 h-10 text-blue-400" />
          <span className="text-slate-300 text-sm text-center">
            Click to select files (any format, multiple allowed)
          </span>
          <input
            type="file"
            multiple
            className="hidden"
            onChange={(e) =>
              setFiles(Array.from(e.target.files || []))
            }
          />
        </label>

        {/* Selected Files */}
        {files.length > 0 && (
          <div className="mt-4 space-y-2 max-h-48 overflow-y-auto border border-white/10 rounded-lg p-3">
            {files.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between gap-3 text-sm text-slate-200"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileIcon className="w-4 h-4 text-blue-400 shrink-0" />
                  <span className="truncate">{file.name}</span>
                </div>
                <span className="text-slate-400 shrink-0">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Status Messages */}
        {status === "success" && (
          <div className="mt-4 flex items-center gap-2 text-green-400 text-sm">
            <CheckCircle className="w-4 h-4" />
            {message}
          </div>
        )}

        {status === "error" && (
          <div className="mt-4 flex items-center gap-2 text-red-400 text-sm">
            <XCircle className="w-4 h-4" />
            {message}
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!files.length || loading}
          className="mt-6 w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white py-3 font-medium transition"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading...
            </>
          ) : (
            `Upload ${files.length} File${files.length === 1 ? "" : "s"}`
          )}
        </button>
      </div>
    </div>
  );
}
