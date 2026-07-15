import { useState, useMemo } from 'react';
import { Plus, X } from 'lucide-react';
import { formatMoney, formatDateString } from '../utils/formatters';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import {
  getPurchaseOrders, createPurchaseOrder, getSuppliers, getLocations, getProducts, getLots,
  sendPurchaseOrder, cancelPurchaseOrder, receivePurchaseOrder,
} from '../api';

const EMPTY_LINE = { product: '', qty_kg: '', qty_pieces: '' };

const STATUS_PILL = {
  draft:     'bg-[#f3f4f6] text-text-secondary',
  sent:      'bg-[#fef3c7] text-[#92400e]',
  received:  'bg-[#dcfce7] text-[#166534]',
  cancelled: 'bg-[#fee2e2] text-[#b91c1c]',
};
const STATUS_LABEL = { draft: 'Draft', sent: 'Sent', received: 'Received', cancelled: 'Cancelled' };

export default function Procurement() {
  const toast = useToast();
  const [showCreate, setShowCreate] = useState(false);
  const [receiving, setReceiving] = useState(null);   // the PO being received
  const [form, setForm] = useState({ supplier: '', notes: '', total_paisa_rs: '' });
  const [receiveForm, setReceiveForm] = useState({ location: '', lot: '', notes: '' });
  const [lines, setLines] = useState([{ ...EMPTY_LINE }]);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');

  const { data: orders, loading, error: loadError, refetch } = useApi(getPurchaseOrders);
  const { data: suppliers } = useApi(getSuppliers);
  const { data: locations } = useApi(getLocations);
  const { data: products } = useApi(getProducts);
  const { data: lots } = useApi(getLots);

  const supplierMap = useMemo(
    () => Object.fromEntries(suppliers.map(s => [s.id, s])),
    [suppliers],
  );

  const openPos = orders.filter(o => o.status === 'draft' || o.status === 'sent');

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createPurchaseOrder({
        supplier: form.supplier,
        notes: form.notes,
        total_paisa: Math.round(parseFloat(form.total_paisa_rs) * 100),
      });
      setShowCreate(false);
      setForm({ supplier: '', notes: '', total_paisa_rs: '' });
      toast.success('Purchase order created');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to create purchase order');
    } finally { setSaving(false); }
  }

  async function handleSend(po) {
    setBusyId(po.id);
    try {
      await sendPurchaseOrder(po.id);
      toast.success(`PO-${po.id} sent to supplier`);
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Could not send this PO');
    } finally { setBusyId(null); }
  }

  async function handleCancel(po) {
    setBusyId(po.id);
    try {
      await cancelPurchaseOrder(po.id);
      toast.success(`PO-${po.id} cancelled`);
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Could not cancel this PO');
    } finally { setBusyId(null); }
  }

  function openReceive(po) {
    setReceiving(po);
    setReceiveForm({ location: '', lot: '', notes: '' });
    setLines([{ ...EMPTY_LINE }]);
    setError('');
  }

  const validLines = lines.filter(
    l => l.product && (parseFloat(l.qty_kg) > 0 || parseInt(l.qty_pieces, 10) > 0),
  );

  async function handleReceive(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await receivePurchaseOrder(receiving.id, {
        location: receiveForm.location,
        lot: receiveForm.lot,
        notes: receiveForm.notes,
        lines: validLines.map(l => ({
          product: Number(l.product),
          qty_kg: l.qty_kg || '0',
          qty_pieces: parseInt(l.qty_pieces, 10) || 0,
          lot: receiveForm.lot ? Number(receiveForm.lot) : null,
        })),
      });
      setReceiving(null);
      toast.success('Goods received — stock is now on hand');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to record this receipt');
    } finally { setSaving(false); }
  }

  function updateLine(index, patch) {
    setLines(ls => ls.map((l, i) => (i === index ? { ...l, ...patch } : l)));
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />

      <div className="flex items-center justify-between mb-5 shrink-0">
        <div className="text-[13px] text-text-secondary">
          {openPos.length} purchase order{openPos.length === 1 ? '' : 's'} awaiting delivery
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2"
        >
          <Plus size={16} /> Purchase Order
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['PO Number', 'Date', 'Supplier', 'Notes', 'Total (Rs)', 'Status', 'Action'].map(h => (
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
                  <td className="px-4 py-3.5 text-text-secondary truncate max-w-[180px]">{po.notes || '—'}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">{po.total_paisa ? formatMoney(po.total_paisa) : '—'}</td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium ${STATUS_PILL[po.status] ?? STATUS_PILL.draft}`}>
                      {STATUS_LABEL[po.status] ?? po.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex gap-3 text-[13px] font-medium">
                      {po.status === 'draft' && (
                        <button onClick={() => handleSend(po)} disabled={busyId === po.id}
                          className="text-brand-primary hover:underline disabled:opacity-50">
                          {busyId === po.id ? '…' : 'Send'}
                        </button>
                      )}
                      {po.status === 'sent' && (
                        <button onClick={() => openReceive(po)}
                          className="text-brand-primary hover:underline">
                          Receive
                        </button>
                      )}
                      {(po.status === 'draft' || po.status === 'sent') && (
                        <button onClick={() => handleCancel(po)} disabled={busyId === po.id}
                          className="text-text-secondary hover:text-brand-danger disabled:opacity-50">
                          Cancel
                        </button>
                      )}
                      {(po.status === 'received' || po.status === 'cancelled') && (
                        <span className="text-text-secondary">—</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {!loading && orders.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-text-secondary text-[14px]">No purchase orders yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create PO */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">Create Purchase Order</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleCreate} className="flex flex-col gap-4">
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Supplier</label>
                <select required value={form.supplier} onChange={e => setForm({ ...form, supplier: e.target.value })} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="">Select Supplier…</option>
                  {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Notes</label>
                <input type="text" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Agreed Total (Rs)</label>
                <input required type="number" min="0" step="0.01" value={form.total_paisa_rs} onChange={e => setForm({ ...form, total_paisa_rs: e.target.value })} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Creating…' : 'Create PO'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Receive goods */}
      {receiving && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[620px] rounded-[20px] shadow-xl p-7 max-h-[90vh] overflow-y-auto">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-1">
              Receive PO-{receiving.id}
            </h2>
            <p className="text-[13px] text-text-secondary mb-5">
              {supplierMap[receiving.supplier]?.name} · what actually arrived, not what was ordered.
            </p>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}

            <form onSubmit={handleReceive} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Delivered to</label>
                  <select required value={receiveForm.location} onChange={e => setReceiveForm({ ...receiveForm, location: e.target.value })} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                    <option value="">Select location…</option>
                    {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Lot (optional)</label>
                  <select value={receiveForm.lot} onChange={e => setReceiveForm({ ...receiveForm, lot: e.target.value })} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                    <option value="">None (feed, supplies…)</option>
                    {lots.map(l => <option key={l.id} value={l.id}>{l.code}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-2">Items received</label>
                <div className="flex flex-col gap-2">
                  {lines.map((line, index) => {
                    const product = products.find(p => p.id === Number(line.product));
                    const isPieces = product?.uom === 'piece';
                    return (
                      <div key={index} className="flex items-start gap-2">
                        <select
                          value={line.product}
                          onChange={e => updateLine(index, { product: e.target.value, qty_kg: '', qty_pieces: '' })}
                          className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white"
                        >
                          <option value="">Select product…</option>
                          {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>

                        <div className="w-[150px] relative">
                          <input
                            type="number" min="0"
                            step={isPieces ? '1' : '0.001'}
                            value={isPieces ? line.qty_pieces : line.qty_kg}
                            onChange={e => updateLine(index, isPieces
                              ? { qty_pieces: e.target.value }
                              : { qty_kg: e.target.value })}
                            placeholder="Qty"
                            className="w-full h-11 border-[1.5px] border-brand-border rounded-md pl-3 pr-10 font-mono text-[14px] focus:border-brand-primary focus:outline-none"
                          />
                          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[12px] text-text-secondary">
                            {isPieces ? 'pcs' : 'kg'}
                          </span>
                        </div>

                        <button
                          type="button"
                          onClick={() => setLines(ls => (ls.length === 1 ? [{ ...EMPTY_LINE }] : ls.filter((_, i) => i !== index)))}
                          className="h-11 w-9 flex items-center justify-center text-text-secondary hover:text-brand-danger transition-colors"
                          title="Remove item"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    );
                  })}
                  <button
                    type="button"
                    onClick={() => setLines(ls => [...ls, { ...EMPTY_LINE }])}
                    className="self-start text-[13px] text-brand-primary hover:underline font-medium flex items-center gap-1 mt-1"
                  >
                    <Plus size={14} /> Add item
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Notes</label>
                <input type="text" value={receiveForm.notes} onChange={e => setReceiveForm({ ...receiveForm, notes: e.target.value })} placeholder="Condition on arrival, short delivery…" className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>

              <p className="text-[12px] text-text-secondary bg-brand-surface border-[1.5px] border-brand-border rounded-md px-3 py-2">
                Recording this receipt adds the items to stock at the chosen location and closes the PO. It cannot be undone.
              </p>

              <div className="flex gap-3">
                <button type="button" onClick={() => setReceiving(null)} className="flex-1 h-12 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button
                  type="submit"
                  disabled={saving || !receiveForm.location || validLines.length === 0}
                  className="flex-1 h-12 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Recording…' : 'Confirm Receipt'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
