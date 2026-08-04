import { useState, useMemo } from 'react';
import { Plus, X, ClipboardList, Send, PackageCheck } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import {
  getPurchaseOrders, createPurchaseOrder, getSuppliers, getLocations, getProducts, getLots,
  sendPurchaseOrder, cancelPurchaseOrder, receivePurchaseOrder,
} from '../api';
import { formatMoney, formatDateString } from '../utils/formatters';
import { useToast } from '../ui/Toast';
import ErrorBanner from '../ui/ErrorBanner';

const EMPTY_LINE = { product: '', qty_kg: '', qty_pieces: '' };

const STATUS_PILL = {
  draft:     'bg-[#f3f4f6] text-text-secondary',
  sent:      'bg-[#fef3c7] text-[#92400e]',
  received:  'bg-[#dcfce7] text-[#166534]',
  cancelled: 'bg-[#fee2e2] text-[#b91c1c]',
};
const STATUS_LABEL = { draft: 'Draft', sent: 'Sent', received: 'Received', cancelled: 'Cancelled' };

export default function PurchaseOrders() {
  const toast = useToast();
  // 'list' | 'create' | PO object being received
  const [view, setView] = useState('list');
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

  const receiving = typeof view === 'object' ? view : null;

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createPurchaseOrder({
        supplier: form.supplier,
        notes: form.notes,
        total_paisa: Math.round(parseFloat(form.total_paisa_rs) * 100),
      });
      setView('list');
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
    setView(po);
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
      setView('list');
      toast.success('Goods received — stock is now on hand');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to record this receipt');
    } finally { setSaving(false); }
  }

  function updateLine(index, patch) {
    setLines(ls => ls.map((l, i) => (i === index ? { ...l, ...patch } : l)));
  }

  /* ── Create form ─────────────────────────────────────────────────────── */
  if (view === 'create') {
    return (
      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm">
        <h3 className="font-sans font-bold text-[18px] text-text-primary mb-4">New Purchase Order</h3>
        {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Supplier</label>
            <select required value={form.supplier} onChange={e => setForm({ ...form, supplier: e.target.value })} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
              <option value="">Select Supplier…</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Agreed Total (Rs)</label>
            <input required type="number" min="0" step="0.01" inputMode="decimal" value={form.total_paisa_rs} onChange={e => setForm({ ...form, total_paisa_rs: e.target.value })} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Notes</label>
            <input type="text" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
          </div>
          <div className="flex gap-3 mt-2">
            <button type="button" onClick={() => setView('list')} className="flex-1 h-12 border-[1.5px] border-brand-border rounded-xl text-text-secondary font-medium">Cancel</button>
            <button type="submit" disabled={saving} className="flex-1 h-12 bg-brand-primary text-white rounded-xl font-sans font-bold disabled:opacity-50 shadow-md">
              {saving ? 'Creating…' : 'Create PO'}
            </button>
          </div>
        </form>
      </div>
    );
  }

  /* ── Receive form ────────────────────────────────────────────────────── */
  if (receiving) {
    return (
      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm">
        <h3 className="font-sans font-bold text-[18px] text-text-primary mb-1">Receive PO-{receiving.id}</h3>
        <p className="text-[13px] text-text-secondary mb-4">
          {supplierMap[receiving.supplier]?.name} · record what actually arrived, not what was ordered.
        </p>
        {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}

        <form onSubmit={handleReceive} className="flex flex-col gap-4">
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Delivered to</label>
            <select required value={receiveForm.location} onChange={e => setReceiveForm({ ...receiveForm, location: e.target.value })} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
              <option value="">Select location…</option>
              {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Lot (optional)</label>
            <select value={receiveForm.lot} onChange={e => setReceiveForm({ ...receiveForm, lot: e.target.value })} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
              <option value="">None (feed, supplies…)</option>
              {lots.map(l => <option key={l.id} value={l.id}>{l.code}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-2">Items received</label>
            <div className="flex flex-col gap-3">
              {lines.map((line, index) => {
                const product = products.find(p => p.id === Number(line.product));
                const isPieces = product?.uom === 'piece';
                return (
                  <div key={index} className="flex items-start gap-2">
                    <div className="flex-1 flex flex-col gap-2">
                      <select
                        value={line.product}
                        onChange={e => updateLine(index, { product: e.target.value, qty_kg: '', qty_pieces: '' })}
                        className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white"
                      >
                        <option value="">Select product…</option>
                        {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                      </select>
                      <div className="relative">
                        <input
                          type="number" min="0"
                          step={isPieces ? '1' : '0.001'}
                          inputMode="decimal"
                          value={isPieces ? line.qty_pieces : line.qty_kg}
                          onChange={e => updateLine(index, isPieces
                            ? { qty_pieces: e.target.value }
                            : { qty_kg: e.target.value })}
                          placeholder="Qty"
                          className="w-full h-12 border-[1.5px] border-brand-border rounded-lg pl-3 pr-12 font-mono text-[14px] focus:border-brand-primary focus:outline-none"
                        />
                        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[12px] text-text-secondary">
                          {isPieces ? 'pcs' : 'kg'}
                        </span>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setLines(ls => (ls.length === 1 ? [{ ...EMPTY_LINE }] : ls.filter((_, i) => i !== index)))}
                      className="h-12 w-9 flex items-center justify-center text-text-secondary hover:text-brand-danger transition-colors"
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
                className="self-start text-[13px] text-brand-primary hover:underline font-medium flex items-center gap-1"
              >
                <Plus size={14} /> Add item
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Notes</label>
            <input type="text" value={receiveForm.notes} onChange={e => setReceiveForm({ ...receiveForm, notes: e.target.value })} placeholder="Condition on arrival, short delivery…" className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
          </div>

          <p className="text-[12px] text-text-secondary bg-brand-surface border-[1.5px] border-brand-border rounded-lg px-3 py-2">
            Recording this receipt adds the items to stock at the chosen location and closes the PO. It cannot be undone.
          </p>

          <div className="flex gap-3">
            <button type="button" onClick={() => setView('list')} className="flex-1 h-12 border-[1.5px] border-brand-border rounded-xl text-text-secondary font-medium">Cancel</button>
            <button
              type="submit"
              disabled={saving || !receiveForm.location || validLines.length === 0}
              className="flex-1 h-12 bg-brand-primary text-white rounded-xl font-sans font-bold disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              {saving ? 'Recording…' : 'Confirm Receipt'}
            </button>
          </div>
        </form>
      </div>
    );
  }

  /* ── PO list ─────────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-4">
      <ErrorBanner error={loadError} onRetry={refetch} />

      <button
        onClick={() => { setForm({ supplier: '', notes: '', total_paisa_rs: '' }); setError(''); setView('create'); }}
        className="w-full h-12 bg-brand-primary text-white rounded-xl font-sans font-bold text-[16px] flex items-center justify-center gap-2 hover:bg-brand-primaryHover transition-colors shadow-md"
      >
        <Plus size={18} /> New Purchase Order
      </button>

      {!loading && orders.length === 0 ? (
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-8 shadow-sm flex flex-col items-center text-center">
          <div className="w-16 h-16 bg-[#f0faf8] text-brand-primary rounded-full flex items-center justify-center mb-4">
            <ClipboardList size={32} />
          </div>
          <h3 className="font-sans font-bold text-[18px] text-text-primary mb-2">No Purchase Orders</h3>
          <p className="text-[14px] text-text-secondary">Create a purchase order to bring in stock from a supplier.</p>
        </div>
      ) : (
        orders.map(po => (
          <div key={po.id} className="bg-white rounded-xl border-[1.5px] border-brand-border p-4 shadow-sm flex flex-col gap-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="font-mono font-bold text-[15px] text-text-primary">PO-{po.id}</span>
                <p className="text-[14px] text-text-primary font-medium mt-0.5">
                  {supplierMap[po.supplier]?.name ?? `Supplier #${po.supplier}`}
                </p>
                <p className="text-[12px] text-text-secondary mt-0.5">
                  {po.created_at ? formatDateString(new Date(po.created_at)) : '—'}
                  {po.total_paisa ? <> · <span className="font-mono">{formatMoney(po.total_paisa)}</span></> : null}
                </p>
                {po.notes && <p className="text-[12px] text-text-secondary mt-1 line-clamp-2">{po.notes}</p>}
              </div>
              <span className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium ${STATUS_PILL[po.status] ?? STATUS_PILL.draft}`}>
                {STATUS_LABEL[po.status] ?? po.status}
              </span>
            </div>

            {(po.status === 'draft' || po.status === 'sent') && (
              <div className="flex gap-2">
                {po.status === 'draft' && (
                  <button onClick={() => handleSend(po)} disabled={busyId === po.id}
                    className="flex-1 h-11 bg-brand-primary text-white rounded-lg font-sans font-semibold text-[14px] flex items-center justify-center gap-1.5 disabled:opacity-50">
                    <Send size={15} /> {busyId === po.id ? 'Sending…' : 'Send to Supplier'}
                  </button>
                )}
                {po.status === 'sent' && (
                  <button onClick={() => openReceive(po)}
                    className="flex-1 h-11 bg-brand-primary text-white rounded-lg font-sans font-semibold text-[14px] flex items-center justify-center gap-1.5">
                    <PackageCheck size={15} /> Receive Goods
                  </button>
                )}
                <button onClick={() => handleCancel(po)} disabled={busyId === po.id}
                  className="h-11 px-4 border-[1.5px] border-brand-border rounded-lg text-text-secondary font-medium text-[14px] hover:text-brand-danger disabled:opacity-50">
                  Cancel
                </button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
