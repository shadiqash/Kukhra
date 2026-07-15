import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Truck, Plus, X } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import {
  getTransfers, getLocations, getProducts, getStockSummary,
  createTransfer, confirmTransferReceipt,
} from '../api';
import { formatDateString } from '../utils/formatters';

const EMPTY_LINE = { product: '', qty: '' };

function Skeleton() {
  return (
    <tr className="border-b border-[#f0f0f0]">
      {Array.from({ length: 6 }).map((_, i) => (
        <td key={i} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
      ))}
    </tr>
  );
}

export default function Transfers() {
  const toast = useToast();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ from_location: '', to_location: '' });
  const [lines, setLines] = useState([{ ...EMPTY_LINE }]);
  const [saving, setSaving] = useState(false);
  const [confirmingId, setConfirmingId] = useState(null);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(null);

  const { data: transfers, loading, error: loadError, refetch } = useApi(getTransfers);
  const { data: locations } = useApi(getLocations);
  const { data: products } = useApi(getProducts);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );
  const productMap = useMemo(
    () => Object.fromEntries(products.map(p => [p.id, p])),
    [products],
  );

  // Stock at the source, so the dispatcher can see what is actually there
  // rather than guessing and being rejected by the server.
  const [sourceStock, setSourceStock] = useState({});
  useEffect(() => {
    if (!form.from_location) { setSourceStock({}); return; }
    let cancelled = false;
    getStockSummary({ location: form.from_location })
      .then(res => {
        if (cancelled) return;
        setSourceStock(Object.fromEntries(
          (res.data.results ?? []).map(r => [r.product, r]),
        ));
      })
      .catch(() => { if (!cancelled) setSourceStock({}); });
    return () => { cancelled = true; };
  }, [form.from_location]);

  const availableFor = (productId) => {
    const row = sourceStock[Number(productId)];
    if (!row) return null;
    const product = productMap[Number(productId)];
    return product?.uom === 'piece'
      ? { qty: row.qty_pieces, unit: 'pcs' }
      : { qty: parseFloat(row.qty_kg), unit: 'kg' };
  };

  // Demand is summed per product, so two lines of the same item are checked
  // against stock together rather than each against the full amount on hand.
  const demandByProduct = useMemo(() => {
    const totals = {};
    for (const l of lines) {
      if (!l.product || !l.qty) continue;
      totals[l.product] = (totals[l.product] ?? 0) + parseFloat(l.qty);
    }
    return totals;
  }, [lines]);

  const lineIsOverStock = (line) => {
    if (!line.product || !line.qty) return false;
    const available = availableFor(line.product);
    return available !== null && demandByProduct[line.product] > available.qty;
  };

  const validLines = lines.filter(l => l.product && parseFloat(l.qty) > 0);
  const canDispatch =
    form.from_location &&
    form.to_location &&
    validLines.length > 0 &&
    !lines.some(lineIsOverStock);

  const inTransit = transfers.filter(t => t.status === 'dispatched');
  const inTransitKg = inTransit.reduce(
    (sum, t) => sum + (t.items ?? []).reduce((s, i) => s + parseFloat(i.qty_kg ?? 0), 0),
    0,
  );

  // Awaiting receipt first — that is the row an admin has to act on.
  const ordered = useMemo(
    () => [...transfers].sort((a, b) => {
      if (a.status !== b.status) return a.status === 'dispatched' ? -1 : 1;
      return new Date(b.dispatched_at) - new Date(a.dispatched_at);
    }),
    [transfers],
  );

  function resetForm() {
    setForm({ from_location: '', to_location: '' });
    setLines([{ ...EMPTY_LINE }]);
    setError('');
  }

  function updateLine(index, patch) {
    setLines(ls => ls.map((l, i) => (i === index ? { ...l, ...patch } : l)));
  }

  async function handleDispatch(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createTransfer({
        from_location: form.from_location,
        to_location: form.to_location,
        dispatched_at: new Date().toISOString(),
        // Quantities go up positive; the server applies the ledger sign.
        lines: validLines.map(l => {
          const product = productMap[Number(l.product)];
          return product?.uom === 'piece'
            ? { product: Number(l.product), qty_pieces: parseInt(l.qty, 10) }
            : { product: Number(l.product), qty_kg: l.qty };
        }),
      });
      setShowModal(false);
      resetForm();
      toast.success('Transfer dispatched');
      refetch();
    } catch (err) {
      const data = err?.response?.data;
      setError(data?.detail ?? data?.non_field_errors?.[0] ?? 'Failed to dispatch transfer');
    } finally { setSaving(false); }
  }

  async function handleConfirm(id) {
    setConfirmingId(id);
    try {
      await confirmTransferReceipt(id);
      toast.success('Transfer received — stock is now at the destination');
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Could not confirm receipt — try again');
    } finally { setConfirmingId(null); }
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />

      <div className="flex items-center justify-between mb-5 shrink-0">
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border px-5 py-3 shadow-sm flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-[#fef3c7] flex items-center justify-center text-[#92400e]">
            <Truck size={18} />
          </div>
          <div>
            <div className="text-[12px] text-text-secondary uppercase tracking-wide">In Transit</div>
            <div className="text-[15px] text-text-primary font-semibold">
              {inTransit.length} transfer{inTransit.length === 1 ? '' : 's'}
              {inTransitKg > 0 && (
                <span className="font-mono text-text-secondary font-normal"> · {inTransitKg.toFixed(3)} kg</span>
              )}
            </div>
          </div>
        </div>

        <button
          onClick={() => { resetForm(); setShowModal(true); }}
          className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2"
        >
          <Plus size={16} /> New Transfer
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['', 'Dispatched', 'From', 'To', 'Items', 'Status', 'Action'].map((h, i) => (
                  <th key={i} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />) : ordered.map(t => {
                const items = t.items ?? [];
                const totalKg = items.reduce((s, i) => s + parseFloat(i.qty_kg ?? 0), 0);
                const isOpen = expanded === t.id;
                return [
                  <tr
                    key={t.id}
                    onClick={() => setExpanded(isOpen ? null : t.id)}
                    className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px] cursor-pointer"
                  >
                    <td className="px-4 py-3.5 text-text-secondary w-8">
                      {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </td>
                    <td className="px-4 py-3.5 text-text-primary">{formatDateString(new Date(t.dispatched_at))}</td>
                    <td className="px-4 py-3.5 text-text-primary">{locationMap[t.from_location]?.name ?? t.from_location}</td>
                    <td className="px-4 py-3.5 text-text-primary">{locationMap[t.to_location]?.name ?? t.to_location}</td>
                    <td className="px-4 py-3.5 text-text-secondary">
                      {items.length} item{items.length === 1 ? '' : 's'}
                      {totalKg > 0 && <span className="font-mono"> · {totalKg.toFixed(3)} kg</span>}
                    </td>
                    <td className="px-4 py-3.5">
                      {t.status === 'dispatched'
                        ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fef3c7] text-[#92400e] font-medium">In transit</span>
                        : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#dcfce7] text-[#166534] font-medium">Received</span>}
                    </td>
                    <td className="px-4 py-3.5">
                      {t.status === 'dispatched' ? (
                        <button
                          onClick={e => { e.stopPropagation(); handleConfirm(t.id); }}
                          disabled={confirmingId === t.id}
                          className="text-[13px] text-brand-primary hover:underline font-medium disabled:opacity-50"
                        >
                          {confirmingId === t.id ? 'Confirming…' : 'Mark Received'}
                        </button>
                      ) : <span className="text-text-secondary">—</span>}
                    </td>
                  </tr>,
                  isOpen && (
                    <tr key={`${t.id}-items`} className="bg-[#fafafa] border-b border-[#f0f0f0]">
                      <td colSpan={7} className="px-12 py-3">
                        {items.length === 0 ? (
                          <span className="text-[13px] text-text-secondary">No line items recorded.</span>
                        ) : (
                          <table className="text-[13px]">
                            <tbody>
                              {items.map((i, idx) => (
                                <tr key={idx}>
                                  <td className="pr-8 py-1 text-text-primary">{i.product_name}</td>
                                  <td className="pr-8 py-1 font-mono text-text-primary">
                                    {parseFloat(i.qty_kg) > 0 ? `${parseFloat(i.qty_kg).toFixed(3)} kg` : ''}
                                    {i.qty_pieces > 0 ? `${i.qty_pieces} pcs` : ''}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </td>
                    </tr>
                  ),
                ];
              })}
              {!loading && transfers.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-text-secondary text-[14px]">No transfers yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[620px] rounded-[20px] shadow-xl p-7 max-h-[90vh] overflow-y-auto">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">New Transfer</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}

            <form onSubmit={handleDispatch} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">From location</label>
                  <select
                    required
                    value={form.from_location}
                    onChange={e => { setForm({ ...form, from_location: e.target.value }); setLines([{ ...EMPTY_LINE }]); }}
                    className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white"
                  >
                    <option value="">Select…</option>
                    {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">To location</label>
                  <select
                    required
                    value={form.to_location}
                    onChange={e => setForm({ ...form, to_location: e.target.value })}
                    className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white"
                  >
                    <option value="">Select…</option>
                    {locations.filter(l => l.id !== parseInt(form.from_location)).map(l => (
                      <option key={l.id} value={l.id}>{l.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-2">Items</label>

                {!form.from_location ? (
                  <p className="text-[13px] text-text-secondary bg-brand-surface border-[1.5px] border-brand-border rounded-md px-3 py-3">
                    Choose a source location to see what is available to send.
                  </p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {lines.map((line, index) => {
                      const available = line.product ? availableFor(line.product) : null;
                      const over = lineIsOverStock(line);
                      const product = productMap[Number(line.product)];
                      const unit = product?.uom === 'piece' ? 'pcs' : 'kg';
                      return (
                        <div key={index} className="flex items-start gap-2">
                          <div className="flex-1">
                            <select
                              value={line.product}
                              onChange={e => updateLine(index, { product: e.target.value })}
                              className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white"
                            >
                              <option value="">Select product…</option>
                              {products.map(p => {
                                const stock = sourceStock[p.id];
                                const qty = p.uom === 'piece'
                                  ? `${stock?.qty_pieces ?? 0} pcs`
                                  : `${parseFloat(stock?.qty_kg ?? 0).toFixed(3)} kg`;
                                return (
                                  <option key={p.id} value={p.id}>{p.name} — {qty} available</option>
                                );
                              })}
                            </select>
                          </div>

                          <div className="w-[150px]">
                            <div className="relative">
                              <input
                                type="number"
                                min="0"
                                step={unit === 'pcs' ? '1' : '0.001'}
                                value={line.qty}
                                onChange={e => updateLine(index, { qty: e.target.value })}
                                placeholder="Qty"
                                className={`w-full h-11 border-[1.5px] rounded-md pl-3 pr-10 font-mono text-[14px] focus:outline-none ${
                                  over ? 'border-brand-danger text-brand-danger' : 'border-brand-border focus:border-brand-primary'
                                }`}
                              />
                              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[12px] text-text-secondary">{unit}</span>
                            </div>
                            {over && available && (
                              <p className="text-[11px] text-brand-danger mt-1">
                                {demandByProduct[line.product] > parseFloat(line.qty)
                                  ? `${demandByProduct[line.product]} ${available.unit} across lines, only ${available.qty} on hand`
                                  : `Only ${available.qty} ${available.unit} on hand`}
                              </p>
                            )}
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
                )}
              </div>

              <div className="flex gap-3 mt-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); resetForm(); }}
                  className="flex-1 h-12 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !canDispatch}
                  className="flex-1 h-12 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Dispatching…' : `Dispatch ${validLines.length || ''} item${validLines.length === 1 ? '' : 's'}`.trim()}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
