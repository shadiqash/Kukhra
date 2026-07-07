import { useApi } from '../hooks/useApi';
import { getProcessingRuns } from '../api';
import { formatDateString } from '../utils/formatters';
import ErrorBanner from '../ui/ErrorBanner';

function Skeleton() {
  return (
    <tr className="border-b border-[#f0f0f0]">
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
      ))}
    </tr>
  );
}

export default function Processing() {
  const { data: runs, loading, error, refetch } = useApi(getProcessingRuns);

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={error} onRetry={refetch} />
      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Date', 'Lot', 'Live Wt (kg)', 'Dressed Wt (kg)', 'Wastage (kg)', 'Yield %', 'Processed By'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />) : runs.map(row => {
                const liveWt = parseFloat(row.input_weight_kg || 0);
                const dressedWt = parseFloat(row.output_weight_kg || 0);
                const wastage = liveWt - dressedWt;
                const yieldPct = liveWt > 0 ? ((dressedWt / liveWt) * 100).toFixed(1) : '—';
                return (
                  <tr key={row.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                    <td className="px-4 py-3.5 text-text-primary">{row.created_at ? formatDateString(new Date(row.created_at)) : '—'}</td>
                    <td className="px-4 py-3.5 font-mono text-brand-primary">{row.lot}</td>
                    <td className="px-4 py-3.5 font-mono text-text-primary">{liveWt.toFixed(3)}</td>
                    <td className="px-4 py-3.5 font-mono text-text-primary">{dressedWt.toFixed(3)}</td>
                    <td className="px-4 py-3.5 font-mono text-brand-danger">{wastage.toFixed(3)}</td>
                    <td className="px-4 py-3.5 font-mono font-medium text-text-primary">{yieldPct !== '—' ? `${yieldPct}%` : '—'}</td>
                    <td className="px-4 py-3.5 text-text-secondary">{row.operator ?? '—'}</td>
                  </tr>
                );
              })}
              {!loading && runs.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-text-secondary text-[14px]">No processing runs yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
