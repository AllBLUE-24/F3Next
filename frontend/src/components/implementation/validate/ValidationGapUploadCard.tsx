'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Upload } from 'lucide-react';
import { getBaseApiUrl } from '@/lib/config';
import { SupervisorInlineUploader } from '../supervisor/SupervisorInlineUploader';

type GapAction = {
  id: string;
  type: string;
  question?: string;
  options?: string[];
  metadata?: {
    tier?: string;
    blocking_unmapped_seeds?: string[];
  };
};

type GapPrompt = {
  id: string;
  step: string;
  status: string;
  actions?: GapAction[];
};

interface Props {
  jobId: string;
  companySlug: string;
  blockingSeeds: string[];
  onDone: () => void;
}

export function ValidationGapUploadCard({
  jobId,
  companySlug,
  blockingSeeds,
  onDone,
}: Props) {
  const [prompts, setPrompts] = useState<GapPrompt[]>([]);
  const [activeUpload, setActiveUpload] = useState<{
    promptId: string;
    actionId: string;
    selectedOption: string;
  } | null>(null);
  const [fetchErr, setFetchErr] = useState<string | null>(null);

  const refreshPrompts = useCallback(async () => {
    try {
      const base = getBaseApiUrl();
      const res = await fetch(`${base}/api/implementation/supervisor-prompts/${jobId}`, {
        cache: 'no-store',
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const open = (Array.isArray(data?.prompts) ? data.prompts : []).filter(
        (p: GapPrompt) =>
          p.status === 'open' &&
          (p.step === 'validation_gap' || p.step === 'validation'),
      );
      setPrompts(open);
      setFetchErr(null);
    } catch (e: unknown) {
      setFetchErr(e instanceof Error ? e.message : 'Failed to load upload prompt');
    }
  }, [jobId]);

  useEffect(() => {
    void refreshPrompts();
    const interval = setInterval(() => void refreshPrompts(), 4000);
    return () => clearInterval(interval);
  }, [refreshPrompts]);

  const prompt = prompts[0];
  const uploadAction =
    prompt?.actions?.find(
      (a) =>
        a.type === 'ask_user' &&
        (a.metadata?.tier === 'critical' || a.id === 'ask_user_missing_mvp_files'),
    ) ?? prompt?.actions?.find((a) => a.type === 'ask_user');

  const seeds =
    uploadAction?.metadata?.blocking_unmapped_seeds?.length
      ? uploadAction.metadata.blocking_unmapped_seeds
      : blockingSeeds;

  const question =
    uploadAction?.question ??
    `Upload data for: ${seeds.join(', ')}. These files are required before import can proceed.`;

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

      {fetchErr && (
        <p className="text-xs text-red-400">{fetchErr}</p>
      )}

      {activeUpload && prompt && uploadAction ? (
        <SupervisorInlineUploader
          projectId={jobId}
          companySlug={companySlug}
          promptId={prompt.id}
          actionId={uploadAction.id}
          selectedOption={activeUpload.selectedOption}
          onSuccess={() => {
            setActiveUpload(null);
            onDone();
          }}
          onCancel={() => setActiveUpload(null)}
        />
      ) : (
        <button
          type="button"
          disabled={!prompt || !uploadAction}
          onClick={() => {
            if (!prompt || !uploadAction) return;
            setActiveUpload({
              promptId: prompt.id,
              actionId: uploadAction.id,
              selectedOption: uploadAction.options?.[0] ?? 'Upload the missing files',
            });
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-red-500/15 border border-red-500/30 hover:bg-red-500/25 disabled:opacity-40 disabled:cursor-not-allowed text-red-200 text-sm font-semibold transition-colors"
        >
          <Upload className="w-4 h-4" />
          {uploadAction?.options?.[0] ?? 'Upload the missing files'}
        </button>
      )}

      {!prompt && !fetchErr && (
        <p className="text-xs text-zinc-500 animate-pulse">
          Preparing upload channel…
        </p>
      )}
    </div>
  );
}
