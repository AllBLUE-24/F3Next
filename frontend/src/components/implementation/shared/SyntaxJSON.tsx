'use client';

import React, { useMemo } from 'react';
import { T } from './tokens';

interface Props {
  data: any;
}

export function SyntaxJSON({ data }: Props) {
  const json = useMemo(() => JSON.stringify(data, null, 2), [data]);
  const lines = json.split('\n');

  return (
    <pre
      className="overflow-x-auto"
      style={{
        margin: 0, padding: '12px 14px', fontSize: 12, lineHeight: '20px',
        fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', 'Geist Mono', monospace",
        background: T.bg, border: `1px solid ${T.borderSub}`, borderRadius: 6,
        color: T.textSec,
      }}
    >
      {lines.map((line, i) => {
        const highlighted = line
          .replace(/"([^"]+)":/g, `<key>"$1"</key>:`)
          .replace(/: "([^"]*)"/g, `: <str>"$1"</str>`)
          .replace(/: (\d+\.?\d*)/g, `: <num>$1</num>`)
          .replace(/: (true|false|null)/g, `: <kw>$1</kw>`);
        return (
          <div key={i} className="flex">
            <span style={{ width: 28, flexShrink: 0, color: T.textTer, userSelect: 'none', textAlign: 'right', paddingRight: 12, fontSize: 11 }}>
              {i + 1}
            </span>
            <span dangerouslySetInnerHTML={{ __html: highlighted }} />
          </div>
        );
      })}
      <style>{`
        pre key { color: #79C0FF; }
        pre str { color: #A5D6FF; }
        pre num { color: #79C0FF; }
        pre kw  { color: #FF7B72; }
      `}</style>
    </pre>
  );
}
