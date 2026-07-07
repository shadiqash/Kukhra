import { useState, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../auth/AuthContext';
import { getMovements, getLocations, getProducts } from '../api';
import { formatDateString } from '../utils/formatters';
import ErrorBanner from '../ui/ErrorBanner';

const TYPE_COLORS = {
  production: 'bg-[#dcfce7] text-[#166534]',
  sale: 'bg-[#ffedd5] text-[#c2410c]',
  transfer: 'bg-[#dbeafe] text-[#1d4ed8]',
  return: 'bg-[#f3e8ff] text-[#7e22ce]',
  wastage: 'bg-[#fee2e2] text-[#b91c1c]',
  adjustment: 'bg-[#f3f4f6] text-[#374151]',
};

function Skeleton() {
  return (
    <tr className="border-b border-[#f0f0f0]">
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i} className="px-4 py-3"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
      ))}
    </tr>
  );
}

export default function Inventory() {
  const { user } = useAuth();

  // Pre-filter to outlet_manager's first assigned location
  const defaultLocation = user?.role === 'outlet_manager' && user?.assigned_locations?.[0]
    ? String(user.assigned_locations[0])
    : '';

  const [locationFilter, setLocationFilter] = useState(defaultLocation);
  const [typeFilter, setTypeFilter] = useState('');

  const params = {};
  if (locationFilter) params.location = locationFilter;
  if (typeFilter) params.type = typeFilter;

  const { data: movements, loading, error, refetch } = useApi(getMovements, params);
  const { data: locations } = useApi(getLocations);
  const { data: products } = useApi(getProducts);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );
  const productMap = useMemo(
    () => Object.fromEntries(products.map(p => [p.id, p])),
    [products],
  );

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={error} onRetry={refetch} />
      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-4 mb-5 flex items-center gap-3 shadow-sm shrink-0">
        <div className="flex items-center gap-2">
          <label className="text-[13px] text-text-secondary">Location:</label>
          <select
            value={locationFilter}
            onChange={e => setLocationFilter(e.target.value)}
            disabled={user?.role === 'outlet_manager'}
            className="w-[180px] h-10 border-[1.5px] border-brand-border rounded-md px-3 font-sans text-[14px] focus:border-brand-primary focus:outline-none bg-white disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <option value="">All Locations</option>
            {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-[13px] text-text-secondary">Type:</label>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="w-[160px] h-10 border-[1.5px] border-brand-border rounded-md px-3 font-sans text-[14px] focus:border-brand-primary focus:outline-none bg-white">
            <option value="">All</option>
            {['production', 'transfer', 'sale', 'return', 'wastage', 'adjustment'].map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Date', 'Type', 'Product', 'Location', 'Qty (kg)', 'Qty (pcs)', 'Lot', 'Ref'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />) : movements.map(m => (
                <tr key={m.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[13px]">
                  <td className="px-4 py-3 text-text-primary">{formatDateString(new Date(m.created_at))}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium capitalize ${TYPE_COLORS[m.type] || TYPE_COLORS.adjustment}`}>{m.type}</span>
                  </td>
                  <td className="px-4 py-3 text-text-primary">{productMap[m.product]?.name ?? m.product}</td>
                  <td className="px-4 py-3 text-text-primary">{locationMap[m.location]?.name ?? m.location}</td>
                  <td className={`px-4 py-3 font-mono ${parseFloat(m.qty_kg) < 0 ? 'text-brand-danger' : parseFloat(m.qty_kg) > 0 ? 'text-brand-success' : 'text-text-secondary'}`}>
                    {m.qty_kg ? (parseFloat(m.qty_kg) > 0 ? `+${parseFloat(m.qty_kg).toFixed(3)}` : parseFloat(m.qty_kg).toFixed(3)) : '—'}
                  </td>
                  <td className={`px-4 py-3 font-mono ${parseInt(m.qty_pieces) < 0 ? 'text-brand-danger' : parseInt(m.qty_pieces) > 0 ? 'text-brand-success' : 'text-text-secondary'}`}>
                    {m.qty_pieces ? (parseInt(m.qty_pieces) > 0 ? `+${m.qty_pieces}` : m.qty_pieces) : '—'}
                  </td>
                  <td className="px-4 py-3 text-text-secondary font-mono text-[12px]">{m.lot || '—'}</td>
                  <td className="px-4 py-3 text-text-secondary">{m.ref_id ? `#${m.ref_id}` : '—'}</td>
                </tr>
              ))}
              {!loading && movements.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-text-secondary text-[14px]">No movements recorded.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-white border-t-[1.5px] border-brand-border px-4 py-3 flex items-center justify-between text-[13px] text-text-secondary shrink-0">
          <span>Showing {movements.length} movement(s)</span>
        </div>
      </div>
    </div>
  );
}
