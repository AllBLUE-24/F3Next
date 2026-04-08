'use client';

import React, { useRef } from 'react';
import {
  UploadCloud, Loader2, Sparkles, ChevronRight,
  AlertTriangle, Layers, Bot, CheckCircle2,
} from 'lucide-react';
import { T } from '../shared/tokens';
import { SyntaxJSON } from '../shared/SyntaxJSON';

interface Props {
  stage: string;
  profile: any;
  validation: any;
  uploading: boolean;
  hovering: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
  onFileSelect: (files: File[]) => void;
  onApprove?: () => void;
}

export function StagePanel({
  stage, profile, validation, uploading, hovering,
  onDragOver, onDragLeave, onDrop, onFileSelect, onApprove,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div
      className="h-full flex flex-col relative"
      style={{ background: T.bg }}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* Stage header */}
      <div
        className="flex items-center justify-between shrink-0 select-none"
        style={{ height: 40, padding: '0 20px', borderBottom: `1px solid ${T.borderSub}`, background: T.surface, fontSize: 12 }}
      >
        <div className="flex items-center gap-1.5" style={{ color: T.textSec }}>
          <Sparkles size={13} style={{ color: T.accent }} />
          <span style={{ fontWeight: 600 }}>Stage</span>
          <ChevronRight size={12} style={{ color: T.textTer }} />
          <span style={{ color: T.textTer }}>{stage.replace(/_/g, ' ')}</span>
        </div>
      </div>

      {/* Drop overlay */}
      {hovering && (
        <div
          className="absolute inset-0 z-50 flex items-center justify-center"
          style={{ background: `${T.accent}0A`, border: `2px dashed ${T.accent}60` }}
        >
          <div className="flex flex-col items-center gap-2">
            <UploadCloud size={28} style={{ color: T.accent }} />
            <span style={{ color: T.accent, fontSize: 13, fontWeight: 600 }}>Drop files to upload</span>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto" style={{ padding: 20 }}>

        {/* Awaiting files — upload zone */}
        {(stage === 'awaiting_files' || (!profile && !validation)) && (
          <div className="h-full flex flex-col items-center justify-center">
            <button
              onClick={() => fileRef.current?.click()}
              className="group flex flex-col items-center justify-center w-full transition-all duration-200"
              style={{
                maxWidth: 520, padding: '52px 36px',
                border: `1px dashed ${T.border}`, borderRadius: 8,
                background: T.surface, cursor: 'pointer',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = T.accent; e.currentTarget.style.background = T.accentMute; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.background = T.surface; }}
            >
              <UploadCloud size={36} style={{ color: T.textTer, marginBottom: 14 }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: T.text, marginBottom: 6 }}>
                Upload implementation data
              </span>
              <span style={{ fontSize: 12, color: T.textTer, textAlign: 'center', maxWidth: 340 }}>
                Drag & drop CSV, XLSX, JSON, or TXT files — or click to browse
              </span>
            </button>
            {uploading && (
              <div className="flex items-center gap-2 mt-6" style={{ color: T.accent, fontSize: 13 }}>
                <Loader2 size={16} className="animate-spin" /> Uploading to secure storage…
              </div>
            )}
          </div>
        )}

        {/* Scanning / Processing */}
        {(stage === 'scanning' || stage === 'inferring_f3iche' || stage === 'building_profile' || stage === 'mapping' || stage === 'validating' || stage === 'building_import_plan') && !profile && !validation && (
          <div className="h-full flex flex-col items-center justify-center">
            <Loader2 size={28} style={{ color: T.accent }} className="animate-spin mb-4" />
            <span style={{ fontSize: 13, color: T.textSec, fontWeight: 500 }}>
              {stage.replace(/_/g, ' ')}…
            </span>
          </div>
        )}

        {/* Profile data */}
        {profile && (
          <div className="space-y-5">
            <div>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Layers size={14} style={{ color: T.accent }} /> Company Profile
              </h3>
              <SyntaxJSON data={{
                f3iche: profile.f3iche,
                industry: profile.industry,
                company_name: profile.company_name,
                modules: profile.modules,
                required_doctypes: profile.required_doctypes,
              }} />
            </div>

            {profile.llm_enrichment && (
              <div>
                <h3 style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Bot size={14} style={{ color: T.accent }} /> LLM Enrichment
                </h3>
                <SyntaxJSON data={profile.llm_enrichment} />
              </div>
            )}
          </div>
        )}

        {/* Validation report */}
        {validation && (
          <div className={profile ? 'mt-5' : ''}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
              <AlertTriangle size={14} style={{ color: validation.overall === 'pass' ? T.success : T.error }} />
              Validation Report
              <span style={{
                fontSize: 10, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase',
                padding: '2px 8px', borderRadius: 4, marginLeft: 6,
                background: validation.overall === 'pass' ? `${T.success}20` : `${T.error}20`,
                color: validation.overall === 'pass' ? T.success : T.error,
              }}>
                {validation.overall}
              </span>
            </h3>
            <SyntaxJSON data={validation} />
          </div>
        )}

        {/* Conditional action prompt */}
        {stage.includes('awaiting') && stage !== 'awaiting_files' && (
          <div
            className="mt-6"
            style={{ padding: '16px 20px', background: T.surface2, border: `1px solid ${T.border}`, borderRadius: 8 }}
          >
            <div className="flex items-center gap-2 mb-2" style={{ fontSize: 12, fontWeight: 600, color: T.warning }}>
              <AlertTriangle size={14} /> Action Required
            </div>
            <p style={{ fontSize: 12, color: T.textSec, marginBottom: 14 }}>
              The pipeline is waiting for your confirmation to proceed.
            </p>
            <button
              onClick={onApprove}
              className="transition-colors duration-150"
              style={{
                padding: '8px 22px', borderRadius: 6, fontSize: 12, fontWeight: 600,
                background: T.accent, color: '#fff', border: 'none', cursor: 'pointer',
              }}
              onMouseEnter={e => e.currentTarget.style.background = T.accentHover}
              onMouseLeave={e => e.currentTarget.style.background = T.accent}
            >
              Approve & Continue
            </button>
          </div>
        )}

        {/* Complete */}
        {stage === 'complete' && (
          <div className="h-full flex flex-col items-center justify-center">
            <CheckCircle2 size={36} style={{ color: T.success, marginBottom: 12 }} />
            <span style={{ fontSize: 15, fontWeight: 600, color: T.text }}>Implementation Complete</span>
            <span style={{ fontSize: 12, color: T.textSec, marginTop: 4 }}>All data has been imported successfully.</span>
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileRef}
        type="file"
        multiple
        className="hidden"
        onChange={e => { if (e.target.files) onFileSelect(Array.from(e.target.files)); }}
      />
    </div>
  );
}
