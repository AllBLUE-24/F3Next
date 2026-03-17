'use client';

// src/components/implementation/analyze/TaskStream.tsx

import { useEffect, useRef } from 'react';
import { CheckCircle, Loader, Circle, AlertTriangle } from 'lucide-react';
import type { AnalysisTask } from '@/types/implementation';

interface Props {
  tasks: AnalysisTask[];
}

const STATUS_ICON = {
  idle:        <Circle className="w-3.5 h-3.5 text-gray-700 flex-shrink-0" />,
  running:     <Loader className="w-3.5 h-3.5 text-amber-400 flex-shrink-0 animate-spin" />,
  done:        <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />,
  needs_input: <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 flex-shrink-0" />,
};

export function TaskStream({ tasks }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll as new tasks come in
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [tasks]);

  return (
    <div className="bg-[#0D0D14] border border-white/[0.06] rounded-xl overflow-hidden">
      {/* Terminal header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
        </div>
        <span className="text-xs text-gray-700 font-mono ml-2">f3next.agent · analysis log</span>
      </div>

      {/* Log entries */}
      <div className="p-4 space-y-3 max-h-64 overflow-y-auto font-mono text-xs">
        {tasks.length === 0 && (
          <p className="text-gray-700 italic">Initializing analysis engine…</p>
        )}
        {tasks.map((task, i) => (
          <div
            key={task.id}
            className={`flex items-start gap-3 transition-opacity duration-500 ${
              task.status === 'idle' ? 'opacity-30' : 'opacity-100'
            }`}
            style={{ animationDelay: `${i * 80}ms` }}
          >
            {STATUS_ICON[task.status]}
            <div className="flex-1 min-w-0">
              <span className={`${
                task.status === 'running' ? 'text-amber-300' :
                task.status === 'done'    ? 'text-gray-400' :
                task.status === 'needs_input' ? 'text-yellow-400' :
                'text-gray-700'
              }`}>
                {task.label}
              </span>
              {task.detail && task.status !== 'idle' && (
                <p className="text-gray-700 mt-0.5 truncate">{task.detail}</p>
              )}
              {task.status === 'running' && (
                <span className="inline-block ml-1 text-amber-500 animate-pulse">▋</span>
              )}
            </div>
            {task.completedAt && (
              <span className="text-gray-800 flex-shrink-0 text-[10px]">
                {new Date(task.completedAt).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}