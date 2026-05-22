"use client";

import { useState, useCallback } from "react";
import { Upload, X, File, AlertCircle, ArrowRight } from "lucide-react";
import { getBaseApiUrl } from "@/lib/config";

interface SupervisorInlineUploaderProps {
  projectId: string;
  companySlug: string;
  promptId: string;
  actionId: string;
  selectedOption: string;
  userNote?: string;
  onSuccess: () => void;
  onCancel: () => void;
}

interface FileEntry {
  id: string;
  name: string;
  size: number;
  file: File;
}

export function SupervisorInlineUploader({
  projectId,
  companySlug,
  promptId,
  actionId,
  selectedOption,
  userNote,
  onSuccess,
  onCancel,
}: SupervisorInlineUploaderProps) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const addFiles = useCallback((incoming: FileList | null) => {
    if (!incoming) return;
    const next: FileEntry[] = Array.from(incoming).map((f) => ({
      id: `${f.name}-${Date.now()}-${Math.random()}`,
      name: f.name,
      size: f.size,
      file: f,
    }));
    setEntries((prev) => [...prev, ...next]);
    setError(null);
  }, []);

  const removeEntry = (id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleUploadAndSubmit = async () => {
    if (!entries.length) return;
    setError(null);
    setIsUploading(true);

    try {
      const base = getBaseApiUrl();

      // Step 1: Respond to the supervisor prompt to notify workflow that we are providing files
      setUploadStep("Registering response with assistant...");
      const respondRes = await fetch(`${base}/api/implementation/supervisor-prompts/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          prompt_id: promptId,
          chosen_action_id: actionId,
          extra_data: {
            selected_option: selectedOption,
            ...(userNote ? { user_note: userNote } : {}),
          },
        }),
      });
      if (!respondRes.ok) {
        throw new Error(`Failed to submit supervisor response: ${await respondRes.text()}`);
      }

      // Step 2: Ask FastAPI for the R2 upload tickets (Presigned URLs)
      setUploadStep("Preparing secure upload channels...");
      const fileNames = entries.map((e) => e.name);
      const presignedRes = await fetch(`${base}/api/implementation/presigned-urls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, file_names: fileNames }),
      });
      if (!presignedRes.ok) {
        throw new Error("Failed to generate presigned upload URLs.");
      }
      const { urls } = await presignedRes.json();

      // Step 3: Upload all files directly to Cloudflare R2 in parallel
      setUploadStep("Uploading data files...");
      const uploadedFilesData: { file_name: string; object_path: string }[] = [];

      await Promise.all(
        entries.map(async (entry) => {
          const fileUrlData = urls.find((u: any) => u.file_name === entry.name);
          if (!fileUrlData) throw new Error(`Missing upload URL for ${entry.name}`);

          const res = await fetch(fileUrlData.upload_url, {
            method: "PUT",
            body: entry.file, // Send raw binary directly to R2
            headers: {
              "Content-Type": entry.file.type || "application/octet-stream",
            },
          });

          if (!res.ok) throw new Error(`Failed to upload ${entry.name} to storage.`);

          uploadedFilesData.push({
            file_name: entry.name,
            object_path: fileUrlData.object_path, // Keep track of where it landed in R2
          });
        })
      );

      // Step 4: Tell FastAPI/Temporal that the files are safe in the quarantine bucket
      setUploadStep("Signalling background workflow...");
      const signalRes = await fetch(`${base}/api/implementation/signal/files-uploaded`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          uploaded_files: uploadedFilesData,
          company_slug: companySlug,
        }),
      });
      if (!signalRes.ok) {
        throw new Error(`Failed to signal workflow: ${await signalRes.text()}`);
      }

      setUploadStep("Completed successfully!");
      // Step 5: Success callback to refresh views
      setTimeout(() => {
        onSuccess();
      }, 1000);
    } catch (err: unknown) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Upload failed. Please try again.");
      setIsUploading(false);
      setUploadStep(null);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="rounded-xl border border-amber-500/25 bg-amber-500/[0.02] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-amber-400">
          Upload Files for Gap Resolution
        </span>
        <button
          onClick={onCancel}
          disabled={isUploading}
          className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          Cancel
        </button>
      </div>

      {/* Drag & Drop area */}
      {!isUploading && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`relative rounded-lg border border-dashed text-center p-5 cursor-pointer transition-colors ${
            isDragging
              ? "border-amber-500 bg-amber-500/5"
              : "border-white/[0.08] bg-white/[0.01] hover:bg-white/[0.02] hover:border-zinc-700"
          }`}
        >
          <label className="cursor-pointer block">
            <input
              type="file"
              multiple
              className="hidden"
              onChange={(e) => addFiles(e.target.files)}
              accept=".sql,.csv,.xlsx,.xls,.json,.xml"
            />
            <Upload className="w-5 h-5 text-zinc-500 mx-auto mb-2" />
            <p className="text-xs text-zinc-300 font-medium">
              Drag & drop files here, or <span className="text-amber-400">browse</span>
            </p>
            <p className="text-[10px] text-zinc-500 mt-1 font-mono">
              CSV · XLSX · JSON · SQL
            </p>
          </label>
        </div>
      )}

      {/* Uploading progress indicator */}
      {isUploading && (
        <div className="rounded-lg border border-white/[0.05] bg-white/[0.01] p-4 text-center space-y-3">
          <div className="w-5 h-5 border-2 border-amber-500/25 border-t-amber-500 rounded-full animate-spin mx-auto" />
          <p className="text-xs font-medium text-zinc-300">{uploadStep}</p>
        </div>
      )}

      {/* Selected file list */}
      {entries.length > 0 && !isUploading && (
        <div className="space-y-1.5 max-h-40 overflow-y-auto">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04] text-xs"
            >
              <div className="flex items-center gap-2 min-w-0">
                <File className="w-3.5 h-3.5 text-zinc-500 flex-shrink-0" />
                <span className="text-zinc-300 truncate font-medium">{entry.name}</span>
                <span className="text-[10px] text-zinc-600 font-mono">{formatBytes(entry.size)}</span>
              </div>
              <button
                onClick={() => removeEntry(entry.id)}
                className="text-zinc-600 hover:text-zinc-300 transition-colors p-0.5 rounded"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 p-2.5 rounded bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p className="leading-normal">{error}</p>
        </div>
      )}

      {/* Submit button */}
      {!isUploading && (
        <button
          onClick={handleUploadAndSubmit}
          disabled={entries.length === 0}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-30 disabled:cursor-not-allowed text-black font-semibold text-xs transition-colors shadow-lg shadow-amber-500/5"
        >
          <span>Upload &amp; Continue</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
