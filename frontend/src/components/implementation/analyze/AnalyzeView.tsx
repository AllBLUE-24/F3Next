'use client';
// PATH: src/components/implementation/analyze/AnalyzeView.tsx

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, CheckCircle } from 'lucide-react';
import { useAnalysis } from '@/hooks/implementation/useAnalysis';
import { BrainVisualizer } from './BrainVisualizer';
import { TaskStream } from './TaskStream';
import type { AnalysisTask } from '@/types/implementation';

interface Props {
  jobId: string;
  validateHref: string;
  devTasks?: AnalysisTask[]; // injected in dev mode — bypasses polling
}

export function AnalyzeView({ jobId, validateHref, devTasks }: Props) {
  const live = useAnalysis(devTasks ? null : jobId); // skip polling if devTasks provided
  const router = useRouter();

  // In dev mode, use the injected tasks; in prod, use polled tasks
  const tasks    = devTasks ?? live.tasks;
  const profile  = live.profile;
  const isDone   = devTasks ? false : (live.isComplete || live.needsInput); // dev stays in "thinking" state

  const doneTasks  = tasks.filter((t) => t.status === 'done').length;
  const totalTasks = tasks.filter((t) => t.status !== 'idle').length || 1;
  const pct        = Math.round((doneTasks / totalTasks) * 100);

  // Auto-advance only in real mode
  useEffect(() => {
    if (!devTasks && (live.isComplete || live.needsInput)) {
      const t = setTimeout(() => router.push(validateHref), 1800);
      return () => clearTimeout(t);
    }
  }, [devTasks, live.isComplete, live.needsInput, router, validateHref]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">Step 02 of 04</p>
        <h1 className="text-3xl font-black text-white mb-3">
          {isDone ? 'Analysis complete.' : 'Analyzing your data.'}
        </h1>
        <p className="text-gray-500 text-base leading-relaxed">
          {isDone
            ? 'We\'ve built your company profile. Review it in the next step.'
            : 'Our agent is reading your files, mapping your data, and building your company profile.'}
        </p>
        {devTasks && (
          <p className="mt-2 text-xs font-mono text-amber-600 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5 inline-block">
            DEV MODE — showing mock tasks, polling disabled
          </p>
        )}
      </div>

      {/* Brain canvas */}
      <div className="relative rounded-2xl overflow-hidden border border-white/[0.06] bg-[#0D0D14]">
        <BrainVisualizer isActive={!isDone} />
        <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isDone ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (
              <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            )}
            <span className="text-xs font-mono text-gray-500">
              {isDone ? 'Agent finished' : 'Agent is thinking…'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-28 h-1 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-500 rounded-full transition-all duration-700"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs font-mono text-gray-600 tabular-nums w-8 text-right">{pct}%</span>
          </div>
        </div>
      </div>

      {/* Task stream */}
      <TaskStream tasks={tasks} />

      {/* Emerging profile teaser */}
      {profile && (
        <div className="bg-white/[0.02] border border-amber-500/20 rounded-xl p-5">
          <p className="text-xs font-bold uppercase tracking-widest text-amber-500 mb-3">Profile emerging</p>
          <div className="grid grid-cols-2 gap-3 text-xs">
            {[
              ['Company', profile.name],
              ['Industry', profile.industry],
              ['Currency', profile.currency],
              ['Modules', profile.modules.slice(0, 3).join(', ') + (profile.modules.length > 3 ? '…' : '')],
            ].map(([k, v]) => (
              <div key={k}>
                <span className="text-gray-700">{k}</span>
                <p className="text-white font-medium mt-0.5">{v}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {isDone && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/20">
          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-400">Analysis complete. Taking you to validation…</p>
          <ArrowRight className="w-4 h-4 text-green-400 ml-auto animate-pulse" />
        </div>
      )}

      {!devTasks && live.error && (
        <p className="text-xs text-red-400 font-mono">{live.error}</p>
      )}
    </div>
  );
}