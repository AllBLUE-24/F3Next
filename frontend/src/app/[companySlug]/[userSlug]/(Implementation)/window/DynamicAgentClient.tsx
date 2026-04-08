'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Panel, PanelGroup } from 'react-resizable-panels';
import axios from 'axios';
import { T } from '@/components/implementation/shared/tokens';
import { ResizeHandle } from '@/components/implementation/shared/ResizeHandle';
import { PipelineSidebar } from '@/components/implementation/panels/PipelineSidebar';
import { StagePanel } from '@/components/implementation/panels/StagePanel';
import { ConsultantChat, type ChatMessage } from '@/components/implementation/panels/ConsultantChat';

interface Props {
  projectId: string;
  companySlug: string;
}

const API = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DynamicAgentClient({ projectId, companySlug }: Props) {
  const [wf, setWf] = useState<any>(null);
  const [prevStage, setPrevStage] = useState('');
  const [uploading, setUploading] = useState(false);
  const [hovering, setHovering] = useState(false);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'consultant', text: 'Welcome to F3Next. I\'m your Implementation Consultant. Upload your data files to begin, or ask me anything about the process.' },
  ]);
  const [chatInput, setChatInput] = useState('');

  const pushChat = useCallback((role: ChatMessage['role'], text: string) => {
    setChatMessages(p => [...p, { role, text }]);
  }, []);

  // ── Poll workflow state ────────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch(`${API()}/api/implementation/state/${projectId}`);
        if (!r.ok) return;
        const d = await r.json();
        setWf(d);
        if (d.stage && d.stage !== prevStage) {
          pushChat('consultant', `Pipeline stage updated → ${d.stage.replace(/_/g, ' ')}`);
          setPrevStage(d.stage);
        }
      } catch { /* silent */ }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, [projectId, prevStage, pushChat]);

  // ── Chat send ──────────────────────────────────────────────────────────────
  const sendChat = () => {
    if (!chatInput.trim()) return;
    pushChat('user', chatInput);
    setChatInput('');
    setTimeout(() => pushChat('consultant', 'Understood. Processing your request.'), 400);
  };

  // ── Upload ─────────────────────────────────────────────────────────────────
  const onDrop = async (e: React.DragEvent) => {
    e.preventDefault(); setHovering(false);
    await upload(Array.from(e.dataTransfer.files));
  };

  const upload = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    pushChat('consultant', `Uploading ${files.length} file(s) to secure storage…`);

    try {
      // Try presigned URL approach first
      let uploaded_files: any[] = [];
      try {
        const { data } = await axios.post(`${API()}/api/implementation/presigned-urls`, {
          project_id: projectId,
          file_names: files.map(f => f.name),
        });
        await Promise.all(files.map(async file => {
          const t = data.urls.find((u: any) => u.file_name === file.name);
          if (t) await axios.put(t.upload_url, file, {
            headers: { 'Content-Type': file.type || 'application/octet-stream' },
          });
        }));
        uploaded_files = data.urls.map((u: any) => ({
          file_name: u.file_name, object_path: u.object_path,
        }));
      } catch {
        // Fallback: proxy through backend
        pushChat('consultant', 'Direct upload failed, using backend proxy…');
        const formData = new FormData();
        formData.append('project_id', projectId);
        files.forEach(f => formData.append('files', f));
        const { data } = await axios.post(`${API()}/api/implementation/upload-files`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        uploaded_files = data.uploaded_files;
      }

      // Signal backend workflow
      await axios.post(`${API()}/api/implementation/signal/files-uploaded`, {
        project_id: projectId, uploaded_files, company_slug: companySlug,
      });
      pushChat('consultant', `All ${files.length} file(s) uploaded. Analysis pipeline triggered.`);
    } catch (err: any) {
      pushChat('consultant', `Upload failed: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setUploading(false);
    }
  };

  // ── Derived state ──────────────────────────────────────────────────────────
  const stage = wf?.stage || 'awaiting_files';
  const tasks = wf?.tasks || [];
  const profile = wf?.f3iche_profile;
  const validation = wf?.validation_report;
  const uploadedFiles = wf?.uploaded_files || [];

  return (
    <div className="h-full w-full" style={{ background: T.bg, color: T.text, fontFamily: "'Inter', -apple-system, sans-serif" }}>
      <PanelGroup direction="horizontal" className="h-full">
        <Panel defaultSize={18} minSize={14} maxSize={28}>
          <PipelineSidebar tasks={tasks} uploadedFiles={uploadedFiles} profile={profile} stage={stage} />
        </Panel>

        <ResizeHandle />

        <Panel defaultSize={48} minSize={30}>
          <StagePanel
            stage={stage}
            profile={profile}
            validation={validation}
            uploading={uploading}
            hovering={hovering}
            onDragOver={e => { e.preventDefault(); setHovering(true); }}
            onDragLeave={() => setHovering(false)}
            onDrop={onDrop}
            onFileSelect={upload}
          />
        </Panel>

        <ResizeHandle />

        <Panel defaultSize={34} minSize={22} maxSize={45}>
          <ConsultantChat
            messages={chatMessages}
            input={chatInput}
            onInputChange={setChatInput}
            onSend={sendChat}
          />
        </Panel>
      </PanelGroup>
    </div>
  );
}
