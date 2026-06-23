'use client';

import { useCallback, useState } from 'react';
import { AlertTriangle, Upload, X, File, AlertCircle, ArrowRight } from 'lucide-react';
import { getBaseApiUrl } from '@/lib/config';

interface Props {
  jobId: string;
  companySlug: string;
  blockingSeeds: string[];
  onDone: () => void;
}

interface FileEntry {
  id: string;
  name: string;
  size: number;
  file: File;
}

export function ValidationGapUploadCard({
  jobId,
  companySlug,
  blockingSeeds,
  onDone,
}: Props) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const seeds = blockingSeeds.filter(Boolean);
  const question =
    seeds.length > 0
      ? `Upload data for: ${seeds.join(', ')}. These files are required before import can proceed.`
      : 'Upload the missing MVP files before import can proceed.';

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
    [addFiles],
  );

  const handleUploadAndSubmit = async () => {
    if (!entries.length) return;
    setError(null);
    setIsUploading(true);

    try {
      const base = getBaseApiUrl();

      setUploadStep('Preparing secure upload channels…');
      const fileNames = entries.map((e) => e.name);
      const presignedRes = await fetch(`${base}/api/implementation/presigned-urls`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: jobId, file_names: fileNames }),
      });
      if (!presignedRes.ok) {
        throw new Error('Failed to generate presigned upload URLs.');
      }
      const { urls } = await presignedRes.json();

      setUploadStep('Uploading data files…');
      const uploadedFilesData: { file_name: string; object_path: string }[] = [];

      await Promise.all(
        entries.map(async (entry) => {
          const fileUrlData = urls.find((u: { file_name: string }) => u.file_name === entry.name);
          if (!fileUrlData) throw new Error(`Missing upload URL for ${entry.name}`);

          const res = await fetch(fileUrlData.upload_url, {
            method: 'PUT',
            body: entry.file,
            headers: {
              'Content-Type': entry.file.type || 'application/octet-stream',
            },
          });
          if (!res.ok) throw new Error(`Failed to upload ${entry.name} to storage.`);

          uploadedFilesData.push({
            file_name: entry.name,
            object_path: fileUrlData.object_path,
          });
        }),
      );

      setUploadStep('Notifying workflow…');
      const signalRes = await fetch(`${base}/api/implementation/signal/files-uploaded`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: jobId,
          uploaded_files: uploadedFilesData,
          company_slug: companySlug,
        }),
      });
      if (!signalRes.ok) {
        throw new Error(`Failed to signal workflow: ${await signalRes.text()}`);
      }

      setUploadStep('Processing — mapping and re-validating…');
      setEntries([]);
      setIsUploading(false);
      setUploadStep(null);
      onDone();
    } catch (err: unknown) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
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
    <div className="rounded-2xl border border-red-500/25 bg-gradient-to-br from-red-950/40 via-transparent to-transparent p-6 space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-red-500/15 border border-red-500/25 flex items-center justify-center flex-shrink-0">
          <AlertTriangle className="w-5 h-5 text-red-400" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-widest text-red-400 mb-1.5">
            Missing MVP data — upload required
          </p>
          <p className="text-white text-sm leading-relaxed">{question}</p>
          {seeds.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {seeds.map((seed) => (
                <span
                  key={seed}
                  className="text-xs bg-red-500/10 border border-red-500/20 text-red-300 px-3 py-1 rounded-full font-medium"
                >
                  {seed}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {!isUploading && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`relative rounded-xl border border-dashed text-center p-6 cursor-pointer transition-colors ${
            isDragging
              ? 'border-red-400 bg-red-500/5'
              : 'border-white/[0.08] bg-white/[0.01] hover:bg-white/[0.02] hover:border-zinc-700'
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
            <Upload className="w-6 h-6 text-zinc-500 mx-auto mb-2" />
            <p className="text-sm text-zinc-300 font-medium">
              Drag & drop files here, or <span className="text-red-300">browse</span>
            </p>
            <p className="text-[11px] text-zinc-500 mt-1 font-mono">
              e.g. stock_entry.csv · CSV · XLSX · JSON
            </p>
          </label>
        </div>
      )}

      {isUploading && (
        <div className="rounded-xl border border-white/[0.05] bg-white/[0.01] p-4 text-center space-y-3">
          <div className="w-5 h-5 border-2 border-red-500/25 border-t-red-400 rounded-full animate-spin mx-auto" />
          <p className="text-xs font-medium text-zinc-300">{uploadStep}</p>
        </div>
      )}

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
                type="button"
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

      {!isUploading && (
        <button
          type="button"
          onClick={() => void handleUploadAndSubmit()}
          disabled={entries.length === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-red-500/15 border border-red-500/30 hover:bg-red-500/25 disabled:opacity-40 disabled:cursor-not-allowed text-red-200 text-sm font-semibold transition-colors"
        >
          <Upload className="w-4 h-4" />
          Upload &amp; continue mapping
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
