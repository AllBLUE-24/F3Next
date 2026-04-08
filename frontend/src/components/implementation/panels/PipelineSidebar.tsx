'use client';

import React from 'react';
import { Activity, FileText, Layers, CheckCircle2, Circle, Play } from 'lucide-react';
import { T } from '../shared/tokens';

interface Task {
  id: string;
  label: string;
  status: string;
  detail?: string;
}

interface Props {
  tasks: Task[];
  uploadedFiles: any[];
  profile: any;
  stage: string;
}

const DEFAULT_TASKS: Task[] = [
  { id: 't1', label: 'File ingestion',    status: 'idle' },
  { id: 't2', label: 'Format detection',  status: 'idle' },
  { id: 't3', label: 'Metadata extract',  status: 'idle' },
  { id: 't4', label: 'F3iche inference',  status: 'idle' },
  { id: 't5', label: 'Target structure',  status: 'idle' },
  { id: 't6', label: 'Field mapping',     status: 'idle' },
  { id: 't7', label: 'Pre-import checks', status: 'idle' },
  { id: 't8', label: 'Import plan',       status: 'idle' },
];

function TaskIcon({ status }: { status: string }) {
  if (status === 'done')    return <CheckCircle2 size={13} style={{ color: T.success }} />;
  if (status === 'running') return <Play size={13} style={{ color: T.accent }} className="animate-pulse" />;
  return <Circle size={13} style={{ color: T.textTer }} />;
}

function SectionLabel({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
  return (
    <div className="flex items-center gap-1.5 mb-3" style={{ fontSize: 11, fontWeight: 600, color: T.textTer, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
      <Icon size={12} /> {label}
    </div>
  );
}

function Divider() {
  return <div style={{ borderTop: `1px solid ${T.borderSub}`, margin: '6px 14px' }} />;
}

export function PipelineSidebar({ tasks, uploadedFiles, profile, stage }: Props) {
  const items = tasks.length ? tasks : DEFAULT_TASKS;

  const stageColor = stage.includes('error') ? T.error
    : stage.includes('complete') ? T.success
    : stage.includes('awaiting') ? T.warning
    : T.accent;

  return (
    <div className="h-full flex flex-col overflow-y-auto" style={{ background: T.surface, borderRight: `1px solid ${T.borderSub}` }}>
      {/* Pipeline */}
      <div style={{ padding: '14px 14px 10px' }}>
        <SectionLabel icon={Activity} label="Pipeline" />
        <div className="space-y-0.5">
          {items.map((t) => (
            <div
              key={t.id}
              className="flex items-center gap-2 transition-colors duration-150"
              style={{
                padding: '5px 8px', borderRadius: 6, fontSize: 12,
                color: t.status === 'running' ? T.text : t.status === 'done' ? T.textSec : T.textTer,
                fontWeight: t.status === 'running' ? 600 : 400,
                background: t.status === 'running' ? T.accentMute : 'transparent',
              }}
            >
              <TaskIcon status={t.status} />
              <span className="truncate">{t.label}</span>
            </div>
          ))}
        </div>
      </div>

      <Divider />

      {/* Payloads */}
      <div style={{ padding: '10px 14px' }}>
        <SectionLabel icon={FileText} label="Payloads" />
        {uploadedFiles?.length ? (
          <div className="space-y-0.5">
            {uploadedFiles.map((f: any, i: number) => (
              <div key={i} className="flex items-center gap-2 truncate" style={{ fontSize: 12, color: T.textSec, padding: '3px 8px' }}>
                <FileText size={11} style={{ color: T.textTer, flexShrink: 0 }} />
                <span className="truncate">{f.file_name || f}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 11, color: T.textTer, padding: '3px 8px' }}>No files uploaded</div>
        )}
      </div>

      <Divider />

      {/* Context */}
      <div style={{ padding: '10px 14px' }}>
        <SectionLabel icon={Layers} label="Context" />
        {profile ? (
          <div className="space-y-1.5" style={{ fontSize: 12 }}>
            {[
              ['Niche', profile.f3iche],
              ['Industry', profile.industry],
              ['Doctypes', profile.required_doctypes?.length ?? '—'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between" style={{ padding: '2px 8px' }}>
                <span style={{ color: T.textTer }}>{k}</span>
                <span style={{ color: T.text, fontWeight: 500 }}>{String(v)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 11, color: T.textTer, padding: '3px 8px' }}>Awaiting analysis</div>
        )}
      </div>

      {/* Stage indicator */}
      <div className="mt-auto" style={{ padding: '10px 14px', borderTop: `1px solid ${T.borderSub}` }}>
        <div className="flex items-center gap-2" style={{ fontSize: 11 }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
            background: stageColor, boxShadow: `0 0 8px ${stageColor}50`,
          }} />
          <span style={{ color: T.textSec, fontWeight: 500 }}>{stage.replace(/_/g, ' ')}</span>
        </div>
      </div>
    </div>
  );
}
