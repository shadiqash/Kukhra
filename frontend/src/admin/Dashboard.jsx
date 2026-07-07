import { useEffect, useState, useMemo } from 'react';
import { Coins, ShoppingBag, AlertTriangle } from 'lucide-react';
import { formatMoney, formatDateString } from '../utils/formatters';
import { getOrders, getLocations } from '../api';

export default function Dashboard() {
  const [recentOrders, setRecentOrders] = useState([]);
  const [locations, setLocations] = useState([]);
  const [todayTotal, setTodayTotal] = useState(0);
  const [todayCount, setTodayCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        // Outlet managers are scoped server-side to their assigned locations.
        const [ordersRes, locationsRes] = await Promise.allSettled([
          getOrders({ page: 1 }),
          getLocations(),
        ]);

        if (ordersRes.status === 'fulfilled') {
          const orders = ordersRes.value.data.results ?? ordersRes.value.data;
          setRecentOrders(orders.slice(0, 5));
          setTodayCount(orders.length);
          setTodayTotal(orders.reduce((s, o) => s + (o.total_paisa ?? 0), 0));
        }

        if (locationsRes.status === 'fulfilled') {
          const locs = locationsRes.value.data.results ?? locationsRes.value.data;
          setLocations(locs);
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
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
      <div className="grid grid-cols-3 gap-4 mb-6 shrink-0">
        <KpiCard label="Recent Revenue" value={formatMoney(todayTotal)} sub={`Latest ${todayCount} orders`} icon={Coins} iconBg="bg-[#f0faf8]" />
        <KpiCard label="Recent Orders" value={String(todayCount)} sub="Most recent page" icon={ShoppingBag} iconBg="bg-[#f0faf8]" />
        <KpiCard label="Low Stock" value="—" sub="Visit Inventory to check" subColor="text-text-secondary" icon={AlertTriangle} iconBg="bg-red-50" />
      </div>

      <div className="flex gap-4 min-h-[400px]">
        {/* Recent Orders */}
        <div className="w-[65%] bg-white rounded-xl border-[1.5px] border-brand-border flex flex-col overflow-hidden shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b-[1.5px] border-brand-border bg-white">
            <h2 className="font-sans font-semibold text-[16px] text-text-primary">Recent Orders</h2>
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

        {/* Low Stock placeholder */}
        <div className="w-[35%] bg-white rounded-xl border-[1.5px] border-brand-border flex flex-col overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b-[1.5px] border-brand-border bg-white">
            <h2 className="font-sans font-semibold text-[16px] text-text-primary">Low Stock Alerts</h2>
          </div>
          <div className="flex-1 flex items-center justify-center px-5 text-center">
            <div>
              <AlertTriangle size={32} className="text-brand-border mx-auto mb-3" />
              <p className="text-[13px] text-text-secondary">Visit the Inventory screen to check current stock levels.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
