'use client';

import React, { useRef, useEffect } from 'react';
import { Send, Bot } from 'lucide-react';
import { T } from '../shared/tokens';

export interface ChatMessage {
  role: 'user' | 'consultant';
  text: string;
}

interface Props {
  messages: ChatMessage[];
  input: string;
  onInputChange: (val: string) => void;
  onSend: () => void;
}

export function ConsultantChat({ messages, input, onInputChange, onSend }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="h-full flex flex-col" style={{ background: T.surface, borderLeft: `1px solid ${T.borderSub}` }}>
      {/* Header */}
      <div
        className="flex items-center gap-2 shrink-0 select-none"
        style={{ height: 40, padding: '0 16px', borderBottom: `1px solid ${T.borderSub}`, background: T.surface2, fontSize: 12 }}
      >
        <Bot size={14} style={{ color: T.accent }} />
        <span style={{ fontWeight: 600, color: T.text }}>Consultant</span>
        <span style={{ fontSize: 10, color: T.textTer, marginLeft: 'auto', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          online
        </span>
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto" style={{ padding: '10px 0' }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            className="transition-opacity duration-200"
            style={{ padding: '7px 16px', fontSize: 13, lineHeight: '20px', color: msg.role === 'user' ? T.text : T.textSec }}
          >
            <div className="flex items-start gap-2">
              <span style={{
                fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em',
                color: msg.role === 'user' ? T.accent : T.textTer,
                width: 28, flexShrink: 0, paddingTop: 3,
              }}>
                {msg.role === 'user' ? 'you' : 'f3'}
              </span>
              <span style={{ wordBreak: 'break-word' }}>{msg.text}</span>
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '10px 12px', borderTop: `1px solid ${T.borderSub}`, background: T.surface2 }}>
        <div
          className="flex items-center gap-2 transition-colors duration-150"
          style={{ padding: '8px 12px', background: T.bg, border: `1px solid ${T.borderSub}`, borderRadius: 8 }}
          onFocus={e => e.currentTarget.style.borderColor = T.accent}
          onBlur={e => e.currentTarget.style.borderColor = T.borderSub}
        >
          <input
            className="flex-1 bg-transparent outline-none"
            style={{ color: T.text, fontSize: 13, fontFamily: 'inherit' }}
            placeholder="Ask the consultant…"
            value={input}
            onChange={e => onInputChange(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && onSend()}
          />
          <button
            onClick={onSend}
            className="transition-all duration-150"
            style={{
              padding: '4px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
              background: input.trim() ? T.accent : 'transparent',
              color: input.trim() ? '#fff' : T.textTer,
            }}
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
