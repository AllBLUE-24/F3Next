'use client';
// PATH: src/components/implementation/upload/UploadView.tsx

import { useCallback, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Upload, File, X, AlertCircle, ArrowRight } from 'lucide-react';
import { getBaseApiUrl } from '@/lib/config';

interface FileEntry {
  id: string;
  name: string;
  size: number;
  file: File; 
}

interface Props {
  projectId: string; // We need this to tell R2 and Temporal which project this is!
  getPresignedUrls: (projectId: string, fileNames: string[]) => Promise<{ urls: { file_name: string, upload_url: string, object_path: string }[] }>;
  signalUploadComplete: (
    projectId: string,
    companySlug: string,
    uploadedFiles: { file_name: string, object_path: string }[],
    userNote?: string
  ) => Promise<any>;
  analyzeHref: string;
}

export function UploadView({ projectId, getPresignedUrls, signalUploadComplete, analyzeHref }: Props) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false); // Swapped useTransition for reliable client-side async loading
  const [error, setError] = useState<string | null>(null);
  const [importNote, setImportNote] = useState("");
  const router = useRouter();
  const params = useParams<{ companySlug: string }>();
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployTriggered, setDeployTriggered] = useState(false);

  const handleDeploy = async () => {
    setIsDeploying(true);
    try {
      const base = getBaseApiUrl();
      const res = await fetch(`${base}/api/deploy/infra`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          company_slug: params?.companySlug || 'unknown',
          tier: 'standard'
        })
      });
      if (res.ok) {
        setDeployTriggered(true);
      } else {
        setError("Instance deployment failed to trigger.");
      }
    } catch(err) {
      console.error(err);
      setError("Network error while deploying instance.");
    } finally {
      setIsDeploying(false);
    }
  };

  const addFiles = useCallback((incoming: FileList | null) => {
    if (!incoming) return;
    const next: FileEntry[] = Array.from(incoming).map((f) => ({
      id: `${f.name}-${Date.now()}-${Math.random()}`,
      name: f.name,
      size: f.size,
      file: f,
    }));
    setEntries((prev) => [...prev, ...next]);
  }, []);

  const removeEntry = (id: string) =>
    setEntries((prev) => prev.filter((e) => e.id !== id));

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleSubmit = async () => {
    if (!entries.length) return;
    setError(null);
    setIsUploading(true);

    try {
      // 1. Ask FastAPI for the R2 upload tickets (Presigned URLs)
      const fileNames = entries.map((e) => e.name);
      const { urls } = await getPresignedUrls(projectId, fileNames);

      const uploadedFilesData: { file_name: string; object_path: string }[] = [];

      // 2. Upload all files directly to Cloudflare R2 in parallel
      await Promise.all(
        entries.map(async (entry) => {
          const fileUrlData = urls.find((u) => u.file_name === entry.name);
          if (!fileUrlData) throw new Error(`Missing upload URL for ${entry.name}`);

          const res = await fetch(fileUrlData.upload_url, {
            method: 'PUT',
            body: entry.file, // Send raw binary directly to R2
            headers: {
              'Content-Type': entry.file.type || 'application/octet-stream',
            },
          });

          if (!res.ok) throw new Error(`Failed to upload ${entry.name}`);

          uploadedFilesData.push({
            file_name: entry.name,
            object_path: fileUrlData.object_path, // Keep track of where it landed in R2
          });
        })
      );

      // 3. Tell FastAPI/Temporal that the files are safe in the quarantine bucket
      await signalUploadComplete(projectId, params?.companySlug || 'unknown', uploadedFilesData, importNote.trim());

      // 4. Move to the next stage
      router.push(`${analyzeHref}?jobId=${projectId}`);
    } catch (err) {
      console.error(err);
      setError('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">Step 01 of 04</p>
        <h1 className="text-3xl font-black text-white mb-3">Upload your data.</h1>
        <p className="text-gray-500 text-base leading-relaxed mb-6">
          Drop in any files you have — ERP backups, Excel exports, CSVs, or mixed formats.
          Our system will figure out the rest.
        </p>

        <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4 mb-4 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-white font-bold text-sm">Anything specific we should know?</h3>
            <span className="text-[10px] uppercase tracking-wider text-gray-600">Optional</span>
          </div>
          <textarea
            value={importNote}
            onChange={(e) => setImportNote(e.target.value)}
            placeholder="Example: These files include both master data and transactional exports. Treat BOM rows as child data, not separate items."
            maxLength={800}
            className="w-full min-h-[88px] rounded-lg bg-black/20 border border-white/[0.06] px-3 py-2 text-sm text-white placeholder:text-gray-600 outline-none focus:border-amber-500/40 resize-y"
          />
          <p className="text-[11px] text-gray-600 leading-relaxed">
            This helps the assistant understand what the files mean before it starts mapping them.
          </p>
        </div>

        {/* --- DEPLOY INSTANCE BUTTON --- */}
        <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5 flex items-center justify-between mb-4">
          <div>
             <h3 className="text-white font-bold text-sm mb-1">Provision Sandbox Instance</h3>
             <p className="text-xs text-gray-500">Deploy the cloud container now so it's ready when analysis finishes.</p>
          </div>
          <button
             type="button"
             onClick={handleDeploy}
             disabled={isDeploying || deployTriggered}
             className="px-6 py-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 text-amber-500 font-bold text-sm transition-all disabled:opacity-50"
          >
             {isDeploying ? 'Deploying...' : deployTriggered ? 'Deploy Triggered ✓' : 'Deploy Now'}
          </button>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`relative rounded-2xl border-2 border-dashed transition-all duration-300 overflow-hidden ${
          isDragging
            ? 'border-amber-500 bg-amber-500/5 scale-[1.01]'
            : 'border-white/[0.1] bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.03]'
        }`}
      >
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.01)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.01)_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />

        <label className="relative flex flex-col items-center justify-center py-16 px-8 text-center cursor-pointer">
          <input
            type="file"
            multiple
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            onChange={(e) => addFiles(e.target.files)}
            accept=".sql,.csv,.xlsx,.xls,.json,.xml,.gz,.zip,.tar,.pdf"
          />
          <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-5 transition-all duration-300 ${
            isDragging ? 'bg-amber-500 scale-110' : 'bg-white/[0.05] border border-white/[0.08]'
          }`}>
            <Upload className={`w-7 h-7 transition-colors duration-300 ${isDragging ? 'text-black' : 'text-gray-500'}`} />
          </div>
          <p className="text-white font-bold text-base mb-1">
            {isDragging ? 'Release to drop' : 'Drag & drop your files here'}
          </p>
          <p className="text-gray-600 text-sm mb-4">or click to browse from your device</p>
          <p className="text-gray-700 text-xs font-mono">
            SQL · CSV · XLSX · JSON · XML · ZIP · PDF
          </p>
        </label>
      </div>

      {/* File list */}
      {entries.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-widest text-gray-600">
            {entries.length} file{entries.length !== 1 ? 's' : ''} queued
          </p>
          <div className="space-y-2">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className="flex items-center gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] group"
              >
                <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center flex-shrink-0">
                  <File className="w-4 h-4 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{entry.name}</p>
                  <p className="text-xs text-gray-600 mt-0.5">{formatBytes(entry.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeEntry(entry.id)}
                  className="opacity-0 group-hover:opacity-100 text-gray-700 hover:text-white transition-all p-1 rounded-lg hover:bg-white/[0.05]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hint */}
      <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-4">
        <p className="text-xs text-gray-600 leading-relaxed">
          <span className="text-gray-400 font-semibold">Don't have clean data?</span>{' '}
          That's fine. Upload what you have — partial data, mixed formats, even old printouts scanned as PDFs.
          Our system will work with whatever you provide and tell you exactly what's missing.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* CTA */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!entries.length || isUploading}
        className="w-full py-4 rounded-xl bg-amber-500 text-black font-black text-base hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-xl shadow-amber-500/10"
      >
        {isUploading ? (
          <>
            <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
            Uploading…
          </>
        ) : (
          <>
            Start Analysis
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </>
        )}
      </button>
    </div>
  );
}