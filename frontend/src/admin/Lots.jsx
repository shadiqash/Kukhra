import { useState, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import { getLots, getSuppliers, getLocations, createLot, transitionLot } from '../api';
import { formatDateString } from '../utils/formatters';

// Mirrors the server's VALID_TRANSITIONS whitelist (apps/lots/models.py).
// The server is the authority; this only decides which buttons to offer.
const NEXT_STATUSES = {
  arrival:    ['grading'],
  grading:    ['storage', 'slaughter'],
  storage:    ['slaughter'],
  slaughter:  ['packaging'],
  packaging:  ['sale'],
  sale:       ['settlement'],
  settlement: [],
};

const STATUS_LABEL = {
  arrival: 'Arrival', grading: 'Grading', storage: 'Storage', slaughter: 'Slaughter',
  packaging: 'Packaging', sale: 'Sale', settlement: 'Settlement',
};

export default function Lots() {
  const toast = useToast();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ code: '', source_type: 'external', supplier: '', arrival_location: '', live_weight_kg: '', bird_count: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [movingId, setMovingId] = useState(null);

  const { data: lots, loading, error: loadError, refetch } = useApi(getLots);
  const { data: suppliers } = useApi(getSuppliers);
  const { data: locations } = useApi(getLocations);

  const supplierMap = useMemo(
    () => Object.fromEntries(suppliers.map(s => [s.id, s])),
    [suppliers],
  );

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createLot({
        code: form.code,
        source_type: form.source_type,
        supplier: form.supplier || null,
        arrival_location: form.arrival_location,
        live_weight_kg: form.live_weight_kg,
        bird_count: parseInt(form.bird_count),
      });
      setShowModal(false);
      setForm({ code: '', source_type: 'external', supplier: '', arrival_location: '', live_weight_kg: '', bird_count: '' });
      toast.success('Lot recorded');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to receive lot');
    } finally { setSaving(false); }
  }

  async function handleTransition(lot, next) {
    setMovingId(lot.id);
    try {
      await transitionLot(lot.id, next);
      toast.success(`${lot.code} moved to ${STATUS_LABEL[next]}`);
      refetch();
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Could not advance this lot');
    } finally { setMovingId(null); }
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />
      <div className="flex justify-end mb-5 shrink-0">
        <button onClick={() => setShowModal(true)} className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2">
          + Receive Lot
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Lot Code', 'Supplier', 'Live Weight (kg)', 'Bird Count', 'Received', 'Status', 'Advance To'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-[#f0f0f0]">
                  {Array.from({ length: 7 }).map((__, j) => <td key={j} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>)}
                </tr>
              )) : lots.map(lot => (
                <tr key={lot.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 font-mono text-brand-primary font-medium">{lot.code}</td>
                  <td className="px-4 py-3.5 text-text-primary">{supplierMap[lot.supplier]?.name ?? '—'}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">{parseFloat(lot.live_weight_kg).toFixed(3)}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">{lot.bird_count ?? '—'}</td>
                  <td className="px-4 py-3.5 text-text-primary">{lot.created_at ? formatDateString(new Date(lot.created_at)) : '—'}</td>
                  <td className="px-4 py-3.5">
                    {lot.status === 'arrival' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#dcfce7] text-[#166534] font-medium">Arrival</span>}
                    {lot.status === 'grading' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fef3c7] text-[#92400e] font-medium">Grading</span>}
                    {lot.status === 'slaughter' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fef3c7] text-[#92400e] font-medium">Slaughter</span>}
                    {lot.status === 'storage' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#e0e7ff] text-[#4338ca] font-medium">Storage</span>}
                    {lot.status === 'packaging' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#e0e7ff] text-[#4338ca] font-medium">Packaging</span>}
                    {lot.status === 'sale' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#f3f4f6] text-text-secondary font-medium">Sale</span>}
                    {lot.status === 'settlement' && <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#f3f4f6] text-text-secondary font-medium">Settlement</span>}
                  </td>
                  <td className="px-4 py-3.5">
                    {(NEXT_STATUSES[lot.status] ?? []).length === 0 ? (
                      <span className="text-text-secondary text-[13px]">Complete</span>
                    ) : (
                      <div className="flex gap-2">
                        {NEXT_STATUSES[lot.status].map(next => (
                          <button
                            key={next}
                            onClick={() => handleTransition(lot, next)}
                            disabled={movingId === lot.id}
                            className="h-8 px-3 border-[1.5px] border-brand-border rounded-md text-[13px] font-medium text-brand-primary hover:bg-brand-surface disabled:opacity-50 transition-colors"
                          >
                            {movingId === lot.id ? '…' : `→ ${STATUS_LABEL[next]}`}
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {!loading && lots.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-text-secondary text-[14px]">No lots received yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">Receive New Lot</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleSave} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Lot Code</label>
                  <input required type="text" value={form.code} onChange={e => setForm({...form, code: e.target.value})} placeholder="e.g. LOT-2083-001" className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none uppercase" />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Source</label>
                  <select value={form.source_type} onChange={e => setForm({...form, source_type: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                    <option value="external">External</option>
                    <option value="own">Own Farm</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Supplier</label>
                <select value={form.supplier} onChange={e => setForm({...form, supplier: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="">None / Own Farm</option>
                  {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Arrival Location</label>
                <select required value={form.arrival_location} onChange={e => setForm({...form, arrival_location: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="">Select Location…</option>
                  {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Live Weight (kg)</label>
                  <input required type="number" min="1" step="0.1" value={form.live_weight_kg} onChange={e => setForm({...form, live_weight_kg: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[15px] focus:border-brand-primary focus:outline-none" />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Bird Count</label>
                  <input required type="number" min="1" value={form.bird_count} onChange={e => setForm({...form, bird_count: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[15px] focus:border-brand-primary focus:outline-none" />
                </div>
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Saving…' : 'Save Lot'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
