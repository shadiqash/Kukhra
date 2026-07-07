import { useApi } from '../hooks/useApi';
import { getAuditLogs } from '../api';
import { formatDateTimeString } from '../utils/formatters';

function Skeleton() {
  return (
    <tr className="border-b border-[#f0f0f0]">
      {Array.from({ length: 5 }).map((_, i) => (
        <td key={i} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
      ))}
    </tr>
  );
}

export default function AuditLog() {
  const { data: logs, loading, error } = useApi(getAuditLogs);

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <div className="flex justify-between items-center mb-5 shrink-0">
        <h2 className="font-sans font-bold text-[18px] text-text-primary">System Audit Log</h2>
        {error && <span className="text-brand-danger text-[13px]">{error}</span>}
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Timestamp', 'User', 'Action', 'Model', 'Details'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} />) : logs.map(log => (
                <tr key={log.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 text-text-primary font-mono text-[13px]">
                    {log.created_at ? formatDateTimeString(log.created_at) : '—'}
                  </td>
                  <td className="px-4 py-3.5 text-brand-primary font-medium">{log.actor}</td>
                  <td className="px-4 py-3.5">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[12px] bg-brand-surface border border-brand-border text-text-primary font-medium">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-text-secondary text-[13px]">{log.model_name}</td>
                  <td className="px-4 py-3.5 text-text-secondary truncate max-w-[300px]" title={JSON.stringify(log.diff)}>
                    {log.object_id ? `#${log.object_id}` : '—'}{log.diff ? ` — ${Object.keys(log.diff).join(', ')}` : ''}
                  </td>
                </tr>
              ))}
              {!loading && logs.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-10 text-center text-text-secondary text-[14px]">No audit events recorded.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
