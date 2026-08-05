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

  const KpiCard = ({ label, value, sub, subColor = 'text-brand-success', icon: Icon, iconBg, iconColor = 'text-brand-primary' }) => (
    <div className="card p-6 relative overflow-hidden group hover:-translate-y-1 cursor-default">
      <div className="absolute -right-4 -top-4 w-24 h-24 bg-gradient-to-br from-brand-primary/5 to-transparent rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
      <div className="text-[13px] font-semibold text-text-secondary uppercase tracking-wider mb-2 relative z-10">{label}</div>
      {loading
        ? <div className="h-10 w-32 bg-border/50 rounded animate-pulse mt-1" />
        : <div className="font-sans font-black text-3xl tracking-tight text-text-primary relative z-10">{value}</div>}
      <div className={`text-[14px] font-medium ${subColor} mt-2 relative z-10`}>{sub}</div>
      <div className={`absolute top-6 right-6 w-12 h-12 ${iconBg} rounded-2xl flex items-center justify-center ${iconColor} shadow-sm group-hover:scale-110 transition-transform duration-300`}>
        <Icon size={24} strokeWidth={2.5} />
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto flex flex-col h-full overflow-y-auto animate-fade-in custom-scrollbar pr-2">
      <ErrorBanner error={error} onRetry={() => setReloadKey(k => k + 1)} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 shrink-0">
        <KpiCard
          label="Today's Revenue"
          value={formatMoney(summary.gross_paisa)}
          sub="Cancelled orders excluded"
          subColor="text-text-secondary"
          icon={Coins}
          iconBg="bg-emerald-500/10 dark:bg-emerald-500/20"
          iconColor="text-emerald-600 dark:text-emerald-400"
        />
        <KpiCard
          label="Today's Orders"
          value={String(summary.order_count)}
          sub="Fulfilled and pending"
          subColor="text-text-secondary"
          icon={ShoppingBag}
          iconBg="bg-blue-500/10 dark:bg-blue-500/20"
          iconColor="text-blue-600 dark:text-blue-400"
        />
        <KpiCard
          label="Low Stock"
          value={String(lowStock.length)}
          sub={lowStock.length ? 'Needs restocking' : 'All products above threshold'}
          subColor={lowStock.length ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}
          icon={AlertTriangle}
          iconBg={lowStock.length ? 'bg-rose-500/10 dark:bg-rose-500/20' : 'bg-emerald-500/10 dark:bg-emerald-500/20'}
          iconColor={lowStock.length ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}
        />
      </div>

      <div className="flex flex-col lg:flex-row gap-6 min-h-[400px]">
        {/* Recent Orders */}
        <div className="w-full lg:w-[65%] card flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-6 py-5 border-b border-border bg-surface-hover/50 backdrop-blur-sm">
            <h2 className="font-sans font-bold text-lg text-text-primary tracking-tight">Recent Orders</h2>
            <Link to="/admin/reports" className="text-[14px] font-semibold text-brand-primary hover:text-brand-primaryHover transition-colors">View all</Link>
          </div>
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left text-[14px]">
              <thead className="bg-surface-active/50 border-b border-border">
                <tr>
                  {['Order #', 'Date', 'Outlet', 'Items', 'Total', 'Status'].map(h => (
                    <th key={h} className="px-6 py-4 font-semibold text-text-secondary uppercase tracking-wider text-[12px]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="hover:bg-surface-hover/50 transition-colors">
                    {Array.from({ length: 6 }).map((__, j) => <td key={j} className="px-6 py-4"><div className="h-5 bg-border/50 rounded animate-pulse" /></td>)}
                  </tr>
                )) : recentOrders.map(o => (
                  <tr key={o.id} className="hover:bg-surface-hover/80 transition-colors cursor-pointer group">
                    <td className="px-6 py-4 font-mono font-medium text-text-primary group-hover:text-brand-primary transition-colors">#{o.id}</td>
                    <td className="px-6 py-4 text-text-secondary">{o.created_at ? formatDateString(new Date(o.created_at)) : '—'}</td>
                    <td className="px-6 py-4 text-text-primary font-medium">{locationMap[o.fulfilled_location]?.name ?? '—'}</td>
                    <td className="px-6 py-4 text-text-secondary">{o.lines?.length ?? '—'}</td>
                    <td className="px-6 py-4 font-mono font-bold text-text-primary">{formatMoney(o.total_paisa ?? 0)}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 text-[12px] px-3 py-1 rounded-full font-bold shadow-sm ${
                        o.status === 'fulfilled' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20'
                          : o.status === 'cancelled' ? 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20'
                      }`}>
                        {o.status ?? '—'}
                      </span>
                    </td>
                  </tr>
                ))}
                {!loading && recentOrders.length === 0 && (
                  <tr><td colSpan={6} className="px-6 py-12 text-center text-text-muted text-[15px] font-medium">No orders yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Low Stock Alerts */}
        <div className="w-full lg:w-[35%] card flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-6 py-5 border-b border-border bg-surface-hover/50 backdrop-blur-sm">
            <h2 className="font-sans font-bold text-lg text-text-primary tracking-tight">Low Stock Alerts</h2>
            <Link to="/admin/stock" className="text-[14px] font-semibold text-brand-primary hover:text-brand-primaryHover transition-colors">View stock</Link>
          </div>

          {loading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 bg-border/50 rounded-xl animate-pulse" />)}
            </div>
          ) : lowStock.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center opacity-70">
              <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mb-4">
                <AlertTriangle size={32} className="text-emerald-600 dark:text-emerald-400" />
              </div>
              <p className="text-[15px] font-medium text-text-secondary">Every product is above its stock threshold.</p>
            </div>
          ) : (
            <ul className="flex-1 overflow-y-auto divide-y divide-border custom-scrollbar">
              {lowStock.map(r => (
                <li key={`${r.product}-${r.location}`} className="px-6 py-4 flex items-center justify-between gap-4 hover:bg-surface-hover/50 transition-colors">
                  <div className="min-w-0">
                    <div className="text-[15px] text-text-primary font-bold truncate tracking-tight">
                      {productMap[r.product]?.name ?? `#${r.product}`}
                    </div>
                    <div className="text-[13px] font-medium text-text-secondary truncate mt-0.5">
                      {locationMap[r.location]?.name ?? `#${r.location}`}
                    </div>
                  </div>
                  <span className="font-mono text-[15px] text-rose-600 dark:text-rose-400 font-bold shrink-0 bg-rose-500/10 px-3 py-1 rounded-lg border border-rose-500/20">
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
