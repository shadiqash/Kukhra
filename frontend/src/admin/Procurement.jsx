import { useState, useMemo } from 'react';
import { formatMoney, formatDateString } from '../utils/formatters';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import { getPurchaseOrders, createPurchaseOrder, getSuppliers } from '../api';

export default function Procurement() {
  const toast = useToast();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ supplier: '', notes: '', total_paisa_rs: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const { data: orders, loading, error: loadError, refetch } = useApi(getPurchaseOrders);
  const { data: suppliers } = useApi(getSuppliers);

  const supplierMap = useMemo(
    () => Object.fromEntries(suppliers.map(s => [s.id, s])),
    [suppliers],
  );

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createPurchaseOrder({
        supplier: form.supplier,
        notes: form.notes,
        total_paisa: Math.round(parseFloat(form.total_paisa_rs) * 100),
      });
      setShowModal(false);
      setForm({ supplier: '', notes: '', total_paisa_rs: '' });
      toast.success('Purchase order created');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to create purchase order');
    } finally { setSaving(false); }
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />
      <div className="flex justify-end mb-5 shrink-0">
        <button onClick={() => setShowModal(true)} className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2">
          + Purchase Order
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['PO Number', 'Date', 'Supplier', 'Notes', 'Total (Rs)', 'Status'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 3 }).map((_, i) => (
                <tr key={i} className="border-b border-[#f0f0f0]">
                  {Array.from({ length: 7 }).map((__, j) => <td key={j} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>)}
                </tr>
              )) : orders.map(po => (
                <tr key={po.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 font-mono text-text-primary">{`PO-${po.id}`}</td>
                  <td className="px-4 py-3.5 text-text-primary">{po.created_at ? formatDateString(new Date(po.created_at)) : '—'}</td>
                  <td className="px-4 py-3.5 text-text-primary font-medium">{supplierMap[po.supplier]?.name ?? po.supplier}</td>
                  <td className="px-4 py-3.5 text-text-secondary truncate max-w-[200px]">{po.notes || '—'}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary text-right">{po.total_paisa ? formatMoney(po.total_paisa) : '—'}</td>
                  <td className="px-4 py-3.5">
                    {po.status === 'draft' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#f3f4f6] text-text-secondary font-medium">Draft</span>}
                    {po.status === 'sent' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fef3c7] text-[#92400e] font-medium">Sent</span>}
                    {po.status === 'received' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#dcfce7] text-[#166534] font-medium">Received</span>}
                    {po.status === 'cancelled' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fee2e2] text-[#b91c1c] font-medium">Cancelled</span>}
                  </td>
                </tr>
              ))}
              {!loading && orders.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-10 text-center text-text-secondary text-[14px]">No purchase orders yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">Create Purchase Order</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleSave} className="flex flex-col gap-4">
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Supplier</label>
                <select required value={form.supplier} onChange={e => setForm({...form, supplier: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="">Select Supplier…</option>
                  {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Notes</label>
                <input type="text" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Total (Rs)</label>
                <input required type="number" min="0" step="0.01" value={form.total_paisa_rs} onChange={e => setForm({...form, total_paisa_rs: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Creating…' : 'Create PO'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
