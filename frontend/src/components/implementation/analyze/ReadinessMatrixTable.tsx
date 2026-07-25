'use client';

export type ReadinessMatrixRow = {
  filename: string;
  doctype: string;
  status: string;
  required_fields?: string[];
  present_fields?: string[];
  missing_fields?: string[];
  in_mvp_scope?: boolean;
};

const STATUS_STYLES: Record<string, string> = {
  ready: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  partial: 'bg-amber-500/15 text-amber-300 border-amber-500/25',
  missing: 'bg-red-500/15 text-red-300 border-red-500/25',
  deferred: 'bg-zinc-500/15 text-zinc-400 border-zinc-500/25',
  overclaim: 'bg-orange-500/15 text-orange-300 border-orange-500/25',
  info: 'bg-zinc-500/10 text-zinc-500 border-zinc-500/20',
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] || STATUS_STYLES.info;
  return (
    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${cls}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export function ReadinessMatrixTable({ rows }: { rows: ReadinessMatrixRow[] }) {
  const scoped = rows.filter((r) => r.in_mvp_scope !== false);
  const display = scoped.length > 0 ? scoped : rows;

  if (display.length === 0) {
    return (
      <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 text-sm text-gray-500">
        Readiness matrix will appear once your files are assessed.
      </div>
    );
  }

  const notable = display.filter(
    (r) => r.status !== 'info' && (r.in_mvp_scope !== false || r.status === 'overclaim'),
  );
  const tableRows = notable.length > 0 ? notable.slice(0, 24) : display.slice(0, 24);

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.06]">
        <h3 className="text-sm font-bold text-white">Coverage matrix</h3>
        <p className="text-xs text-gray-500 mt-1">Which Day-1 modules your uploads support</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-gray-600 border-b border-white/[0.04]">
              <th className="px-4 py-3 font-semibold">Module</th>
              <th className="px-4 py-3 font-semibold">File</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold hidden sm:table-cell">Present</th>
              <th className="px-4 py-3 font-semibold hidden md:table-cell">Still needed</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, idx) => (
              <tr
                key={`${row.filename}-${row.doctype}-${idx}`}
                className="border-b border-white/[0.03] hover:bg-white/[0.02]"
              >
                <td className="px-4 py-3 text-white font-medium">{row.doctype}</td>
                <td className="px-4 py-3 text-gray-400 truncate max-w-[140px]">{row.filename || '—'}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={row.status || 'missing'} />
                </td>
                <td className="px-4 py-3 text-gray-500 hidden sm:table-cell">
                  {(row.present_fields || []).slice(0, 4).join(', ') || '—'}
                  {(row.present_fields || []).length > 4 ? '…' : ''}
                </td>
                <td className="px-4 py-3 text-gray-500 hidden md:table-cell">
                  {(row.missing_fields || []).slice(0, 4).join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
