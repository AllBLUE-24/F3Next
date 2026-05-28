'use client';

import { usePathname, useParams } from 'next/navigation';

export function UniversalHeader() {
  const pathname = usePathname();
  const params = useParams<{ companySlug: string; userSlug: string }>();
  
  const companySlug = params?.companySlug ?? '';
  const userSlug    = params?.userSlug ?? '';

  const getTitle = () => {
    if (pathname.includes('/command')) return 'ERP-OS';
    if (pathname.includes('/upload') || pathname.includes('/analyze') || pathname.includes('/validate') || pathname.includes('/import') || pathname.includes('/sandbox')) return 'IMPLEMENTATION';
    if (pathname.includes('/discovery')) return 'DISCOVERY';
    if (pathname.includes('/home')) return 'HOME';
    if (pathname.includes('/profile')) return 'PROFILE';
    if (pathname.includes('/infra')) return 'INFRASTRUCTURE';
    if (pathname.includes('/recommendation')) return 'RECOMMENDATION';
    return 'WORKSPACE';
  };

  const title = getTitle();

  return (
    <div
      style={{
        height: "56px",
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingInline: "24px",
        flexShrink: 0,
        background: "var(--bg-shell)",
        fontFamily: "var(--font-mono), 'IBM Plex Mono', monospace"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span style={{ color: "#f59e0b", fontSize: "11px", fontWeight: 700, letterSpacing: "2px", textTransform: 'uppercase' }}>
          {title}
        </span>
      </div>

      {companySlug && userSlug && (
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ color: "#71717a", fontSize: "11px", letterSpacing: "0.5px", textTransform: 'capitalize' }}>
            {companySlug.replace(/-/g, ' ')}
          </span>
          <span style={{ color: "var(--border-strong)", fontSize: "10px" }}>│</span>
          <span style={{ color: "#52525b", fontSize: "11px", textTransform: 'capitalize' }}>
            {userSlug.replace(/-/g, ' ')}
          </span>
          <span style={{ marginLeft: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span
              style={{
                width: "5px", height: "5px", borderRadius: "50%", background: "#22c55e",
                boxShadow: "0 0 6px #22c55e", animation: "pulse 2s ease-in-out infinite",
              }}
            />
            <span style={{ color: "#52525b", fontSize: "10px", letterSpacing: "1.5px", fontWeight: 500 }}>LIVE</span>
          </span>
        </div>
      )}
    </div>
  );
}
