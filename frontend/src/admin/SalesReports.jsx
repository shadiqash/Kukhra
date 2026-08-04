import { useState, useMemo } from 'react';
import { formatMoney, formatDateString } from '../utils/formatters';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../auth/AuthContext';
import { getOrders, getLocations } from '../api';
import ErrorBanner from '../ui/ErrorBanner';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

export default function SalesReports() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);

  const outletFilter = user?.role === 'outlet_manager' && user?.assigned_locations?.[0]
    ? { fulfilled_location: user.assigned_locations[0] }
    : {};

  const { data: orders, loading, error, refetch } = useApi(getOrders, { page, ...outletFilter });
  const { data: locations } = useApi(getLocations);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );

  // Only fulfilled orders count as revenue — mirrors the backend's orders/summary
  // rule (apps/sales/views.py) and the Dashboard's "cancelled orders excluded" total.
  // Cancelled orders still appear in the table below for record-keeping, but must
  // not contribute to the Page Total.
  const totalGross = orders
    .filter((o) => o.status !== 'cancelled')
    .reduce((s, o) => s + (o.total_paisa ?? 0), 0);

  // Group data by date for the chart
  const chartData = useMemo(() => {
    if (!orders || orders.length === 0) return [];
    
    // Group by YYYY-MM-DD (cancelled orders excluded — see totalGross above)
    const grouped = orders.filter((o) => o.status !== 'cancelled').reduce((acc, order) => {
      if (!order.created_at) return acc;
      const date = order.created_at.split('T')[0];
      if (!acc[date]) acc[date] = 0;
      acc[date] += (order.total_paisa ?? 0) / 100; // Convert to Rs for charting
      return acc;
    }, {});
    
    // Sort and format for Recharts
    return Object.entries(grouped)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, total]) => ({
        date: formatDateString(new Date(date)).split(',')[0], // Just the date part
        revenue: total
      }));
  }, [orders]);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-surface-active rounded-xl p-4 shadow-xl border border-border">
          <p className="text-text-secondary text-xs font-bold uppercase mb-1">{label}</p>
          <p className="text-text-primary text-lg font-mono font-bold">
            Rs {payload[0].value.toLocaleString()}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col gap-6">
      <ErrorBanner error={error} onRetry={refetch} />

      {/* Revenue Chart Section */}
      <div className="glass rounded-3xl p-6 shadow-md shrink-0">
        <h2 className="font-sans font-bold text-[18px] text-text-primary mb-6">Revenue Trend (Current Page)</h2>
        <div className="h-[240px] w-full">
          {loading ? (
            <div className="w-full h-full bg-surface-active rounded-xl animate-pulse border border-border" />
          ) : chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#006e5f" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#006e5f" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis 
                  dataKey="date" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 11, fill: '#6b7280', fontWeight: 600 }}
                  dy={10}
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 11, fill: '#6b7280', fontWeight: 600, fontFamily: 'monospace' }}
                  tickFormatter={(val) => `Rs ${val}`}
                  dx={-10}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#006e5f', strokeWidth: 2, strokeDasharray: '4 4' }} />
                <Area 
                  type="monotone" 
                  dataKey="revenue" 
                  stroke="#006e5f" 
                  strokeWidth={3}
                  fillOpacity={1} 
                  fill="url(#colorRevenue)" 
                  activeDot={{ r: 6, fill: '#006e5f', stroke: '#fff', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-full flex items-center justify-center text-text-secondary font-medium">
              Not enough data to display chart.
            </div>
          )}
        </div>
      </div>

      <div className="glass rounded-3xl overflow-hidden shadow-md flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1 p-2">
          <table className="w-full text-left text-sm border-separate border-spacing-y-1">
            <thead className="bg-surface-active sticky top-0 z-10 backdrop-blur-md rounded-xl">
              <tr>
                {['Order #', 'Date', 'Outlet', 'Items', 'Total'].map(h => (
                  <th key={h} className="px-4 py-3 text-[11px] font-sans font-bold text-text-secondary uppercase tracking-widest text-right first:text-left [&:nth-child(2)]:text-left [&:nth-child(3)]:text-left [&:nth-child(4)]:text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="bg-surface rounded-xl">
                  {Array.from({ length: 5 }).map((__, j) => <td key={j} className="px-4 py-4 rounded-xl"><div className="h-5 bg-surface-active rounded animate-pulse" /></td>)}
                </tr>
              )) : orders.map(o => (
                <tr key={o.id} className="bg-surface hover:bg-surface-hover transition-colors rounded-xl shadow-sm group border border-border">
                  <td className="px-4 py-3.5 font-mono text-brand-primary font-bold rounded-l-xl">#{o.id}</td>
                  <td className="px-4 py-3.5 text-text-primary font-medium">{o.created_at ? formatDateString(new Date(o.created_at)) : '—'}</td>
                  <td className="px-4 py-3.5 text-text-primary">{locationMap[o.fulfilled_location]?.name ?? '—'}</td>
                  <td className="px-4 py-3.5 text-text-primary">{o.lines?.length ?? '—'}</td>
                  <td className="px-4 py-3.5 font-mono font-black text-text-primary text-right rounded-r-xl">{formatMoney(o.total_paisa ?? 0)}</td>
                </tr>
              ))}
              {orders.length > 0 && (
                <tr className="bg-surface-hover border border-border font-semibold text-[14px] rounded-xl shadow-sm">
                  <td colSpan={4} className="px-4 py-4 text-text-primary text-right rounded-l-xl">Page Total</td>
                  <td className="px-4 py-4 font-mono font-black text-brand-primary text-right text-lg rounded-r-xl">{formatMoney(totalGross)}</td>
                </tr>
              )}
              {!loading && orders.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-text-secondary text-[14px]">No sales recorded yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-surface-active border-t border-border px-6 py-4 flex items-center justify-between text-[13px] text-text-secondary shrink-0 font-medium">
          <span>Page {page}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-4 py-2 border border-border bg-surface rounded-xl hover:bg-surface-hover disabled:opacity-40 transition-colors shadow-sm font-bold text-text-primary">Prev</button>
            <button onClick={() => setPage(p => p + 1)} disabled={orders.length < 50} className="px-4 py-2 border border-border bg-surface rounded-xl hover:bg-surface-hover disabled:opacity-40 transition-colors shadow-sm font-bold text-text-primary">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
