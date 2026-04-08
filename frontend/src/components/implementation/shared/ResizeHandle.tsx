'use client';

import { PanelResizeHandle } from 'react-resizable-panels';
import { T } from './tokens';

export function ResizeHandle() {
  return (
    <PanelResizeHandle
      className="group relative flex items-center justify-center"
      style={{ width: 5, background: 'transparent', cursor: 'col-resize' }}
    >
      {/* Visible line on hover */}
      <div
        className="transition-all duration-200 opacity-0 group-hover:opacity-100 group-active:opacity-100"
        style={{
          width: 2, height: '100%',
          background: T.accent, borderRadius: 1,
        }}
      />
      {/* Wider hit area glow */}
      <div
        className="absolute transition-all duration-200 opacity-0 group-hover:opacity-40 group-active:opacity-60"
        style={{
          width: 14, height: '100%',
          background: T.accentMute, borderRadius: 2,
        }}
      />
    </PanelResizeHandle>
  );
}
