import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Coins, ShoppingBag, AlertTriangle } from 'lucide-react';
import { formatMoney, formatDateString } from '../utils/formatters';
import { getOrders, getOrderSummary, getStockSummary, getLocations, getProducts } from '../api';
import ErrorBanner from '../ui/ErrorBanner';

export default function Dashboard() {
  const [recentOrders, setRecentOrders] = useState([]);
  const [locations, setLocations] = useState([]);
  const [products, setProducts] = useState([]);
  const [summary, setSummary] = useState({ order_count: 0, gross_paisa: 0 });
  const [lowStock, setLowStock] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const today = new Date().toISOString().slice(0, 10);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // Outlet managers are scoped server-side to their assigned locations.
        const [summaryRes, ordersRes, stockRes, locationsRes, productsRes] = await Promise.all([
          getOrderSummary({ date_from: today, date_to: today }),
          getOrders({ page: 1 }),
          getStockSummary(),
          getLocations(),
          getProducts(),
        ]);
        if (cancelled) return;

        setSummary(summaryRes.data);

        const orders = ordersRes.data.results ?? ordersRes.data;
        setRecentOrders(orders.slice(0, 5));

        setLowStock((stockRes.data.results ?? []).filter(r => r.low_stock));
        setLocations(locationsRes.data.results ?? locationsRes.data);
        setProducts(productsRes.data.results ?? productsRes.data);
      } catch (e) {
        if (!cancelled) setError(e?.response?.data?.detail ?? e?.message ?? 'Could not load the dashboard');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [today, reloadKey]);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );
  const productMap = useMemo(
    () => Object.fromEntries(products.map(p => [p.id, p])),
    [products],
  );

  const KpiCard = ({ label, value, sub, subColor = 'text-brand-success', icon: Icon, iconBg }) => (
    <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm relative">
      <div className="text-[12px] text-text-secondary uppercase tracking-wide mb-1">{label}</div>
      {loading
        ? <div className="h-8 w-32 bg-gray-100 rounded animate-pulse mt-1" />
        : <div className="font-mono font-bold text-[28px] text-text-primary">{value}</div>}
      <div className={`text-[13px] ${subColor} mt-1`}>{sub}</div>
      <div className={`absolute top-5 right-6 w-10 h-10 ${iconBg} rounded-full flex items-center justify-center text-brand-primary`}>
        <Icon size={20} />
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto flex flex-col h-full overflow-y-auto">
      <ErrorBanner error={error} onRetry={() => setReloadKey(k => k + 1)} />

      <div className="grid grid-cols-3 gap-4 mb-6 shrink-0">
        <KpiCard
          label="Today's Revenue"
          value={formatMoney(summary.gross_paisa)}
          sub="Cancelled orders excluded"
          subColor="text-text-secondary"
          icon={Coins}
          iconBg="bg-[#f0faf8]"
        />
        <KpiCard
          label="Today's Orders"
          value={String(summary.order_count)}
          sub="Fulfilled and pending"
          subColor="text-text-secondary"
          icon={ShoppingBag}
          iconBg="bg-[#f0faf8]"
        />
        <KpiCard
          label="Low Stock"
          value={String(lowStock.length)}
          sub={lowStock.length ? 'Needs restocking' : 'All products above threshold'}
          subColor={lowStock.length ? 'text-brand-danger' : 'text-brand-success'}
          icon={AlertTriangle}
          iconBg={lowStock.length ? 'bg-red-50' : 'bg-[#f0faf8]'}
        />
      </div>

      <div className="flex gap-4 min-h-[400px]">
        {/* Recent Orders */}
        <div className="w-[65%] bg-white rounded-xl border-[1.5px] border-brand-border flex flex-col overflow-hidden shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b-[1.5px] border-brand-border bg-white">
            <h2 className="font-sans font-semibold text-[16px] text-text-primary">Recent Orders</h2>
            <Link to="/admin/reports" className="text-[13px] text-brand-primary hover:underline">View all</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-brand-surface border-b-[1.5px] border-brand-border">
                <tr>
                  {['Order #', 'Date', 'Outlet', 'Items', 'Total', 'Status'].map(h => (
                    <th key={h} className="px-4 py-2.5 font-medium text-text-secondary uppercase tracking-wide text-[11px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i} className="border-b border-[#f0f0f0]">
                    {Array.from({ length: 6 }).map((__, j) => <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>)}
                  </tr>
                )) : recentOrders.map(o => (
                  <tr key={o.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa]">
                    <td className="px-4 py-3 font-mono text-text-primary">#{o.id}</td>
                    <td className="px-4 py-3 text-text-primary">{o.created_at ? formatDateString(new Date(o.created_at)) : '—'}</td>
                    <td className="px-4 py-3 text-text-primary">{locationMap[o.fulfilled_location]?.name ?? '—'}</td>
                    <td className="px-4 py-3 text-text-primary">{o.lines?.length ?? '—'}</td>
                    <td className="px-4 py-3 font-mono text-text-primary">{formatMoney(o.total_paisa ?? 0)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-[12px] px-2 py-0.5 rounded-full font-medium ${
                        o.status === 'fulfilled' ? 'bg-[#dcfce7] text-brand-success'
                          : o.status === 'cancelled' ? 'bg-[#fef2f2] text-brand-danger'
                          : 'bg-[#fef3c7] text-[#92400e]'
                      }`}>
                        {o.status ?? '—'}
                      </span>
                    </td>
                  </tr>
                ))}
                {!loading && recentOrders.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-text-secondary text-[13px]">No orders yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Low Stock Alerts */}
        <div className="w-[35%] bg-white rounded-xl border-[1.5px] border-brand-border flex flex-col overflow-hidden shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b-[1.5px] border-brand-border bg-white">
            <h2 className="font-sans font-semibold text-[16px] text-text-primary">Low Stock Alerts</h2>
            <Link to="/admin/stock" className="text-[13px] text-brand-primary hover:underline">View stock</Link>
          </div>

          {loading ? (
            <div className="p-5 space-y-3">
              {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />)}
            </div>
          ) : lowStock.length === 0 ? (
            <div className="flex-1 flex items-center justify-center px-5 text-center">
              <div>
                <AlertTriangle size={32} className="text-brand-border mx-auto mb-3" />
                <p className="text-[13px] text-text-secondary">Every product is above its stock threshold.</p>
              </div>
            </div>
          ) : (
            <ul className="flex-1 overflow-y-auto divide-y divide-[#f0f0f0]">
              {lowStock.map(r => (
                <li key={`${r.product}-${r.location}`} className="px-5 py-3 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[14px] text-text-primary font-medium truncate">
                      {productMap[r.product]?.name ?? `#${r.product}`}
                    </div>
                    <div className="text-[12px] text-text-secondary truncate">
                      {locationMap[r.location]?.name ?? `#${r.location}`}
                    </div>
                  </div>
                  <span className="font-mono text-[14px] text-brand-danger font-semibold shrink-0">
                    {parseFloat(r.qty_kg).toFixed(3)} kg
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
