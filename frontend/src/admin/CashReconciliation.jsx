import { useMemo, useState } from 'react';
import { Wallet, TrendingDown, DoorOpen } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getCashReconciliation } from '../api';
import { formatMoney, formatDateString } from '../utils/formatters';
import ErrorBanner from '../ui/ErrorBanner';

function Skeleton() {
  return (
    <tr className="border-b border-[#f0f0f0]">
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
      ))}
    </tr>
  );
}

/** Short drawers are the whole point of this screen, so they read loudest. */
function Variance({ paisa }) {
  if (paisa === null || paisa === undefined) {
    return <span className="text-text-secondary">—</span>;
  }
  if (paisa === 0) {
    return <span className="font-mono text-brand-success font-medium">Balanced</span>;
  }
  const short = paisa < 0;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full font-mono text-[13px] font-semibold ${
      short ? 'bg-[#fee2e2] text-[#b91c1c]' : 'bg-[#fef3c7] text-[#92400e]'
    }`}>
      {short ? '−' : '+'}{formatMoney(Math.abs(paisa))}
    </span>
  );
}

export default function CashReconciliation() {
  const [showOnly, setShowOnly] = useState('all');   // all | discrepancies | open

  const { data: sessions, loading, error, refetch } = useApi(getCashReconciliation);

  const stats = useMemo(() => {
    const closed = sessions.filter(s => !s.is_open);
    const short = closed.filter(s => s.variance_paisa < 0);
    // Net across the day: overs partly cancel shorts, but shorts are what you chase.
    const netVariance = closed.reduce((sum, s) => sum + (s.variance_paisa ?? 0), 0);
    const totalShort = short.reduce((sum, s) => sum + s.variance_paisa, 0);
    return {
      openCount: sessions.filter(s => s.is_open).length,
      shortCount: short.length,
      netVariance,
      totalShort,
    };
  }, [sessions]);

  const visible = useMemo(() => {
    const rows = sessions.filter(s => {
      if (showOnly === 'open') return s.is_open;
      if (showOnly === 'discrepancies') return !s.is_open && s.variance_paisa !== 0;
      return true;
    });
    // Biggest shortfalls first — that is the row to act on.
    return [...rows].sort((a, b) => {
      const av = a.variance_paisa ?? 0;
      const bv = b.variance_paisa ?? 0;
      return av - bv;
    });
  }, [sessions, showOnly]);

  const Stat = ({ label, value, sub, tone = 'default', icon: Icon }) => (
    <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm relative flex-1">
      <div className="text-[12px] text-text-secondary uppercase tracking-wide mb-1">{label}</div>
      {loading
        ? <div className="h-8 w-28 bg-gray-100 rounded animate-pulse mt-1" />
        : <div className={`font-mono font-bold text-[26px] ${
            tone === 'danger' ? 'text-brand-danger' : tone === 'success' ? 'text-brand-success' : 'text-text-primary'
          }`}>{value}</div>}
      <div className="text-[13px] text-text-secondary mt-1">{sub}</div>
      <div className={`absolute top-5 right-6 w-10 h-10 rounded-full flex items-center justify-center ${
        tone === 'danger' ? 'bg-red-50 text-brand-danger' : 'bg-[#f0faf8] text-brand-primary'
      }`}>
        <Icon size={20} />
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={error} onRetry={refetch} />

      <div className="flex gap-4 mb-5 shrink-0">
        <Stat
          label="Cash Short"
          value={stats.totalShort === 0 ? formatMoney(0) : formatMoney(Math.abs(stats.totalShort))}
          sub={`${stats.shortCount} shift${stats.shortCount === 1 ? '' : 's'} came up short`}
          tone={stats.totalShort < 0 ? 'danger' : 'success'}
          icon={TrendingDown}
        />
        <Stat
          label="Net Variance"
          value={`${stats.netVariance < 0 ? '−' : ''}${formatMoney(Math.abs(stats.netVariance))}`}
          sub="Overs and shorts combined"
          tone={stats.netVariance < 0 ? 'danger' : 'default'}
          icon={Wallet}
        />
        <Stat
          label="Open Shifts"
          value={String(stats.openCount)}
          sub="Not yet counted"
          icon={DoorOpen}
        />
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-3 mb-5 flex items-center gap-2 shadow-sm shrink-0">
        {[
          { key: 'all', label: 'All shifts' },
          { key: 'discrepancies', label: 'Discrepancies only' },
          { key: 'open', label: 'Open' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setShowOnly(tab.key)}
            className={`h-9 px-4 rounded-md text-[13px] font-medium transition-colors ${
              showOnly === tab.key
                ? 'bg-brand-primary text-white'
                : 'text-text-secondary hover:bg-brand-surface'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Shift', 'Cashier', 'Till', 'Sales', 'Expected Cash', 'Counted', 'Variance', 'Status'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} />) : visible.map(s => (
                <tr key={s.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 text-text-primary">
                    {formatDateString(new Date(s.opened_at))}
                    <span className="block text-[12px] text-text-secondary">{s.location_name}</span>
                  </td>
                  <td className="px-4 py-3.5 text-text-primary font-medium">{s.cashier}</td>
                  <td className="px-4 py-3.5 text-text-secondary">{s.counter}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">
                    {formatMoney(s.sales_total_paisa)}
                    <span className="block text-[12px] text-text-secondary font-sans">
                      {s.sales_count} order{s.sales_count === 1 ? '' : 's'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">
                    {formatMoney(s.expected_cash_paisa)}
                    <span className="block text-[12px] text-text-secondary font-sans">
                      float {formatMoney(s.opening_float_paisa)} + cash {formatMoney(s.cash_sales_paisa)}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">
                    {s.closing_counted_paisa === null ? '—' : formatMoney(s.closing_counted_paisa)}
                  </td>
                  <td className="px-4 py-3.5"><Variance paisa={s.variance_paisa} /></td>
                  <td className="px-4 py-3.5">
                    {s.is_open
                      ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fef3c7] text-[#92400e] font-medium">Open</span>
                      : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#f3f4f6] text-text-secondary font-medium">Closed</span>}
                  </td>
                </tr>
              ))}
              {!loading && visible.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-text-secondary text-[14px]">
                    {sessions.length === 0
                      ? 'No shifts recorded yet.'
                      : showOnly === 'discrepancies'
                        ? 'Every counted drawer balanced.'
                        : 'No shifts match this filter.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-white border-t-[1.5px] border-brand-border px-4 py-3 text-[13px] text-text-secondary shrink-0">
          Showing {visible.length} of {sessions.length} shift(s)
        </div>
      </div>
    </div>
  );
}
