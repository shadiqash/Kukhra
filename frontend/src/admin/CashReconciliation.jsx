import { useMemo, useState } from 'react';
import { Wallet, TrendingDown, DoorOpen } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getCashReconciliation, closeSession } from '../api';
import { formatMoney, formatDateString } from '../utils/formatters';
import { useAuth } from '../auth/AuthContext';
import { useToast } from '../ui/Toast';
import { apiErrorMessage } from '../utils/errors';
import ErrorBanner from '../ui/ErrorBanner';

// A shift left open (device crash, forgotten close, cashier logged out) blocks
// its counter from ever opening a new shift — there was previously no way to
// recover from this except direct DB access. The backend already lets any
// manager/superuser close someone else's session (CashierSession.close() has
// no cashier-identity check); this panel is the missing frontend for it.
// Outlet managers are read-only here (OutletManagerReadOnly on the backend),
// so the action is hidden for that role rather than offering a button that
// would 403.
function ForceCloseModal({ session, onDone, onCancel }) {
  const [counted, setCounted] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const toast = useToast();

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await closeSession(session.id, { closing_counted_paisa: Math.round(parseFloat(counted) * 100) });
      toast.success(`Shift closed — ${session.cashier} @ ${session.counter}`);
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to close shift'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[90] p-4">
      <div className="bg-surface border border-border rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="font-bold text-lg text-text-primary mb-1">Force Close Shift</h2>
        <p className="text-[13px] text-text-secondary mb-4">
          {session.cashier} · {session.counter} — opened {formatDateString(new Date(session.opened_at))}.
          This counts the drawer on the cashier's behalf; use it only when the
          original cashier can no longer close it themselves.
        </p>
        {error && <p className="text-brand-danger bg-brand-danger/10 border border-brand-danger/20 rounded-lg p-3 text-sm font-medium mb-4">{error}</p>}
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-sm font-bold text-text-secondary mb-1.5 block">Counted Cash (Rs)</label>
            <input
              type="number" min="0" step="0.01" required autoFocus
              value={counted}
              onChange={(e) => setCounted(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-[15px] font-semibold focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 focus:outline-none transition-all text-text-primary"
            />
          </div>
          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onCancel} className="flex-1 bg-surface border border-border text-text-primary py-2.5 rounded-xl text-[15px] font-bold hover:bg-surface-hover transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="flex-1 bg-brand-danger hover:bg-red-800 text-white py-2.5 rounded-xl text-[15px] font-bold disabled:opacity-50 transition-colors">
              {loading ? 'Closing…' : 'Close Shift'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Skeleton() {
  return (
    <tr className="bg-surface rounded-xl border border-border">
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i} className="px-4 py-4"><div className="h-4 bg-surface-active rounded animate-pulse" /></td>
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
    <span className={`inline-flex items-center px-2.5 py-1 rounded-md shadow-sm border font-mono text-[13px] font-bold ${
      short ? 'bg-brand-danger/10 text-brand-danger border-brand-danger/20' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
    }`}>
      {short ? '−' : '+'}{formatMoney(Math.abs(paisa))}
    </span>
  );
}

export default function CashReconciliation() {
  const [showOnly, setShowOnly] = useState('all');   // all | discrepancies | open
  const [closingSession, setClosingSession] = useState(null);
  const { hasRole } = useAuth();
  const canForceClose = hasRole('manager', 'superuser');

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
    <div className="glass rounded-[24px] border border-border p-6 shadow-md relative flex-1 group hover:shadow-lg transition-all animate-fade-in-up">
      <div className="text-[12px] text-text-secondary font-bold uppercase tracking-widest mb-1.5">{label}</div>
      {loading
        ? <div className="h-8 w-28 bg-surface-active rounded animate-pulse mt-1" />
        : <div className={`font-mono font-black text-[28px] tracking-tight ${
            tone === 'danger' ? 'text-brand-danger' : tone === 'success' ? 'text-brand-success' : 'text-text-primary'
          }`}>{value}</div>}
      <div className="text-[13px] text-text-secondary mt-1.5 font-medium">{sub}</div>
      <div className={`absolute top-6 right-6 w-12 h-12 rounded-xl flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform ${
        tone === 'danger' ? 'bg-brand-danger/10 text-brand-danger border border-brand-danger/20' : 'bg-brand-primary/10 text-brand-primary border border-brand-primary/20'
      }`}>
        <Icon size={24} />
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

      <div className="bg-surface rounded-xl border border-border p-3 mb-5 flex items-center gap-2 shadow-sm shrink-0">
        {[
          { key: 'all', label: 'All shifts' },
          { key: 'discrepancies', label: 'Discrepancies only' },
          { key: 'open', label: 'Open' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setShowOnly(tab.key)}
            className={`h-9 px-4 rounded-lg text-[13px] font-bold transition-all shadow-sm ${
              showOnly === tab.key
                ? 'bg-gradient-to-r from-brand-primary to-brand-primaryHover text-white border-transparent'
                : 'text-text-secondary hover:bg-surface-hover border border-transparent hover:border-border'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="glass rounded-3xl overflow-hidden shadow-md flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1 p-2">
          <table className="w-full text-left whitespace-nowrap text-sm border-separate border-spacing-y-1">
            <thead className="bg-surface-active sticky top-0 z-10 backdrop-blur-md rounded-xl">
              <tr>
                {['Shift', 'Cashier', 'Till', 'Sales', 'Expected Cash', 'Counted', 'Variance', 'Status', ...(canForceClose ? ['Action'] : [])].map(h => (
                  <th key={h} className="px-4 py-3 text-[11px] font-sans font-bold text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} />) : visible.map(s => (
                <tr key={s.id} className="bg-surface hover:bg-surface-hover transition-colors rounded-xl shadow-sm text-[14px] group border border-border">
                  <td className="px-4 py-3.5 text-text-primary font-medium rounded-l-xl">
                    {formatDateString(new Date(s.opened_at))}
                    <span className="block text-[12px] text-text-secondary font-semibold mt-0.5">{s.location_name}</span>
                  </td>
                  <td className="px-4 py-3.5 text-text-primary font-bold">{s.cashier}</td>
                  <td className="px-4 py-3.5 text-text-secondary">{s.counter}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">
                    <span className="font-bold">{formatMoney(s.sales_total_paisa)}</span>
                    <span className="block text-[12px] text-text-secondary font-sans font-medium mt-0.5">
                      {s.sales_count} order{s.sales_count === 1 ? '' : 's'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">
                    <span className="font-bold">{formatMoney(s.expected_cash_paisa)}</span>
                    <span className="block text-[12px] text-text-secondary font-sans font-medium mt-0.5">
                      float {formatMoney(s.opening_float_paisa)} + cash {formatMoney(s.cash_sales_paisa)}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-text-primary font-black text-[15px]">
                    {s.closing_counted_paisa === null ? '—' : formatMoney(s.closing_counted_paisa)}
                  </td>
                  <td className="px-4 py-3.5"><Variance paisa={s.variance_paisa} /></td>
                  <td className={`px-4 py-3.5 ${canForceClose ? '' : 'rounded-r-xl'}`}>
                    {s.is_open
                      ? <span className="inline-flex items-center px-2.5 py-1 rounded-md shadow-sm border border-amber-500/20 text-[11px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400">Open</span>
                      : <span className="inline-flex items-center px-2.5 py-1 rounded-md shadow-sm border border-border text-[11px] font-bold bg-surface-active text-text-secondary">Closed</span>}
                  </td>
                  {canForceClose && (
                    <td className="px-4 py-3.5 rounded-r-xl">
                      {s.is_open && (
                        <button
                          onClick={() => setClosingSession(s)}
                          className="text-[12px] font-bold text-brand-danger hover:underline"
                        >
                          Force Close
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {!loading && visible.length === 0 && (
                <tr>
                  <td colSpan={canForceClose ? 9 : 8} className="px-4 py-10 text-center text-text-secondary text-[14px]">
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
        <div className="bg-surface-active border-t border-border px-6 py-4 text-[13px] text-text-secondary shrink-0 font-medium">
          Showing {visible.length} of {sessions.length} shift(s)
        </div>
      </div>

      {closingSession && (
        <ForceCloseModal
          session={closingSession}
          onCancel={() => setClosingSession(null)}
          onDone={() => { setClosingSession(null); refetch(); }}
        />
      )}
    </div>
  );
}
