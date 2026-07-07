import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../auth/AuthContext';
import { getInvoices } from '../api';
import { printInvoice } from './printInvoice';
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

export default function Invoices() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);

  const outletFilter = user?.role === 'outlet_manager' && user?.assigned_locations?.[0]
    ? { order__fulfilled_location: user.assigned_locations[0] }
    : {};

  const { data: invoices, loading, error, refetch } = useApi(getInvoices, { page, ...outletFilter });

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={error} onRetry={refetch} />
      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Invoice #', 'Issued', 'Customer', 'Taxable (Rs)', 'VAT (Rs)', 'Total (Rs)', 'CBMS', 'Action'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest text-right first:text-left [&:nth-child(2)]:text-left [&:nth-child(3)]:text-left [&:nth-child(7)]:text-left [&:nth-child(8)]:text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} />) : invoices.map(inv => (
                <tr key={inv.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[13px]">
                  <td className="px-4 py-3.5 font-mono text-text-primary">{inv.invoice_number}</td>
                  <td className="px-4 py-3.5 text-text-primary">{formatDateString(new Date(inv.issued_at))}</td>
                  <td className="px-4 py-3.5 text-text-primary">{inv.customer_name ?? '— (walk-in)'}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary text-right">{formatMoney(inv.taxable_paisa)}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary text-right">{formatMoney(inv.vat_paisa)}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary text-right">{formatMoney(inv.total_paisa)}</td>
                  <td className="px-4 py-3.5">
                    {inv.cbms_status === 'synced' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#dcfce7] text-[#166534] font-medium">Synced</span>}
                    {inv.cbms_status === 'pending' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fef3c7] text-[#92400e] font-medium">Pending</span>}
                    {inv.cbms_status === 'failed' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fee2e2] text-[#b91c1c] font-medium">Failed</span>}
                  </td>
                  <td className="px-4 py-3.5">
                    <button onClick={() => printInvoice(inv)} className="text-[13px] text-brand-primary hover:underline">Print</button>
                  </td>
                </tr>
              ))}
              {!loading && invoices.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-text-secondary text-[14px]">No invoices yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="bg-white border-t-[1.5px] border-brand-border px-4 py-3 flex items-center justify-between text-[13px] text-text-secondary shrink-0">
          <span>Page {page}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 border-[1.5px] border-brand-border rounded-md hover:bg-gray-50 disabled:opacity-40">Prev</button>
            <button onClick={() => setPage(p => p + 1)} disabled={invoices.length < 50} className="px-3 py-1 border-[1.5px] border-brand-border rounded-md hover:bg-gray-50 disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
