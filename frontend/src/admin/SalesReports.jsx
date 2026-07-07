import { useState, useMemo } from 'react';
import { formatMoney } from '../utils/formatters';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../auth/AuthContext';
import { getOrders, getLocations } from '../api';
import { formatDateString } from '../utils/formatters';

export default function SalesReports() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);

  const outletFilter = user?.role === 'outlet_manager' && user?.assigned_locations?.[0]
    ? { fulfilled_location: user.assigned_locations[0] }
    : {};

  const { data: orders, loading, error } = useApi(getOrders, { page, ...outletFilter });
  const { data: locations } = useApi(getLocations);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );

  const totalGross = orders.reduce((s, o) => s + (o.total_paisa ?? 0), 0);

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      {error && <div className="mb-4 bg-red-50 text-brand-danger text-[13px] px-4 py-3 rounded-xl border border-red-200">{error}</div>}

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Order #', 'Date', 'Outlet', 'Items', 'Total'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest text-right first:text-left [&:nth-child(2)]:text-left [&:nth-child(3)]:text-left [&:nth-child(4)]:text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-[#f0f0f0]">
                  {Array.from({ length: 5 }).map((__, j) => <td key={j} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>)}
                </tr>
              )) : orders.map(o => (
                <tr key={o.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 font-mono text-text-primary">#{o.id}</td>
                  <td className="px-4 py-3.5 text-text-primary">{o.created_at ? formatDateString(new Date(o.created_at)) : '—'}</td>
                  <td className="px-4 py-3.5 text-text-primary">{locationMap[o.fulfilled_location]?.name ?? '—'}</td>
                  <td className="px-4 py-3.5 text-text-primary">{o.lines?.length ?? '—'}</td>
                  <td className="px-4 py-3.5 font-mono font-semibold text-text-primary text-right">{formatMoney(o.total_paisa ?? 0)}</td>
                </tr>
              ))}
              {orders.length > 0 && (
                <tr className="bg-brand-surface font-semibold text-[14px]">
                  <td colSpan={4} className="px-4 py-3.5 text-text-primary">Page total</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary text-right">{formatMoney(totalGross)}</td>
                </tr>
              )}
              {!loading && orders.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-text-secondary text-[14px]">No sales recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-white border-t-[1.5px] border-brand-border px-4 py-3 flex items-center justify-between text-[13px] text-text-secondary shrink-0">
          <span>Page {page}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 border-[1.5px] border-brand-border rounded-md hover:bg-gray-50 disabled:opacity-40">Prev</button>
            <button onClick={() => setPage(p => p + 1)} disabled={orders.length < 50} className="px-3 py-1 border-[1.5px] border-brand-border rounded-md hover:bg-gray-50 disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
