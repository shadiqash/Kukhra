import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../auth/AuthContext';
import { getStockSummary, getLocations, getProducts } from '../api';
import ErrorBanner from '../ui/ErrorBanner';

function Skeleton() {
  return (
    <tr className="border-b border-[#f0f0f0]">
      {Array.from({ length: 5 }).map((_, i) => (
        <td key={i} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
      ))}
    </tr>
  );
}

export default function StockOnHand() {
  const { user } = useAuth();

  // Outlet managers are scoped server-side; pre-select their outlet so the
  // filter shown matches the rows they actually get back.
  const defaultLocation = user?.role === 'outlet_manager' && user?.assigned_locations?.[0]
    ? String(user.assigned_locations[0])
    : '';

  const [locationFilter, setLocationFilter] = useState(defaultLocation);
  const [search, setSearch] = useState('');
  const [lowOnly, setLowOnly] = useState(false);

  // The summary envelope carries both the rows and the threshold they were
  // flagged against, so it is fetched directly rather than through useApi,
  // which would unwrap `results` and discard the threshold.
  const [rows, setRows] = useState([]);
  const [threshold, setThreshold] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const { data: locations } = useApi(getLocations);
  const { data: products } = useApi(getProducts);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getStockSummary(locationFilter ? { location: locationFilter } : {})
      .then(res => {
        if (cancelled) return;
        setRows(res.data.results ?? []);
        setThreshold(res.data.threshold_kg ?? null);
      })
      .catch(e => {
        if (!cancelled) setError(e?.response?.data?.detail ?? e?.message ?? 'Could not load stock');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [locationFilter, reloadKey]);

  const refetch = () => setReloadKey(k => k + 1);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );
  const productMap = useMemo(
    () => Object.fromEntries(products.map(p => [p.id, p])),
    [products],
  );

  const visible = useMemo(() => {
    const term = search.trim().toLowerCase();
    return rows.filter(r => {
      if (lowOnly && !r.low_stock) return false;
      if (!term) return true;
      const name = productMap[r.product]?.name ?? '';
      return name.toLowerCase().includes(term);
    });
  }, [rows, lowOnly, search, productMap]);

  const lowCount = rows.filter(r => r.low_stock).length;

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

        <input
          type="search"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search product…"
          className="w-[220px] h-10 border-[1.5px] border-brand-border rounded-md px-3 font-sans text-[14px] focus:border-brand-primary focus:outline-none"
        />

        <label className="flex items-center gap-2 text-[13px] text-text-secondary cursor-pointer ml-auto">
          <input
            type="checkbox"
            checked={lowOnly}
            onChange={e => setLowOnly(e.target.checked)}
            className="w-4 h-4 rounded border-brand-border text-brand-primary focus:ring-brand-primary"
          />
          Low stock only
          {lowCount > 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fee2e2] text-[#b91c1c] font-medium">
              {lowCount}
            </span>
          )}
        </label>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Product', 'Location', 'On Hand (kg)', 'On Hand (pcs)', 'Status'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />) : visible.map(r => (
                <tr key={`${r.product}-${r.location}`} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 text-text-primary font-medium">{productMap[r.product]?.name ?? `#${r.product}`}</td>
                  <td className="px-4 py-3.5 text-text-primary">{locationMap[r.location]?.name ?? `#${r.location}`}</td>
                  <td className={`px-4 py-3.5 font-mono ${r.low_stock ? 'text-brand-danger font-semibold' : 'text-text-primary'}`}>
                    {parseFloat(r.qty_kg).toFixed(3)}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">{r.qty_pieces || '—'}</td>
                  <td className="px-4 py-3.5">
                    {r.low_stock
                      ? <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[12px] bg-[#fee2e2] text-[#b91c1c] font-medium">
                          <AlertTriangle size={12} /> Low
                        </span>
                      : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#dcfce7] text-[#166534] font-medium">OK</span>}
                  </td>
                </tr>
              ))}
              {!loading && visible.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-text-secondary text-[14px]">
                    {rows.length === 0 ? 'No stock recorded yet.' : 'No products match these filters.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-white border-t-[1.5px] border-brand-border px-4 py-3 flex items-center justify-between text-[13px] text-text-secondary shrink-0">
          <span>Showing {visible.length} of {rows.length} product/location pair(s)</span>
          {threshold !== null && <span>Low-stock threshold: {threshold} kg</span>}
        </div>
      </div>
    </div>
  );
}
