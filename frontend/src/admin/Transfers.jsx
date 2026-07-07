import { useState, useMemo } from 'react';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import { getTransfers, getLocations, createTransfer, confirmTransferReceipt } from '../api';
import { formatDateString } from '../utils/formatters';

function Skeleton() {
  return (
    <tr className="border-b border-[#f0f0f0]">
      {Array.from({ length: 5 }).map((_, i) => (
        <td key={i} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>
      ))}
    </tr>
  );
}

export default function Transfers() {
  const toast = useToast();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ from_location: '', to_location: '' });
  const [saving, setSaving] = useState(false);
  const [confirmingId, setConfirmingId] = useState(null);
  const [error, setError] = useState('');

  const { data: transfers, loading, error: loadError, refetch } = useApi(getTransfers);
  const { data: locations } = useApi(getLocations);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );

  async function handleDispatch(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createTransfer({ ...form, dispatched_at: new Date().toISOString() });
      setShowModal(false);
      setForm({ from_location: '', to_location: '' });
      toast.success('Transfer dispatched');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to create transfer');
    } finally { setSaving(false); }
  }

  async function handleConfirm(id) {
    setConfirmingId(id);
    try {
      await confirmTransferReceipt(id);
      toast.success('Transfer received');
      refetch();
    } catch {
      toast.error('Could not confirm receipt — try again');
    }
    finally { setConfirmingId(null); }
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />
      <div className="flex justify-end mb-5 shrink-0">
        <button onClick={() => setShowModal(true)} className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2">
          + Transfer
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Date', 'From', 'To', 'Status', 'Action'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} />) : transfers.map(t => (
                <tr key={t.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 text-text-primary">{formatDateString(new Date(t.dispatched_at))}</td>
                  <td className="px-4 py-3.5 text-text-primary">{locationMap[t.from_location]?.name ?? t.from_location}</td>
                  <td className="px-4 py-3.5 text-text-primary">{locationMap[t.to_location]?.name ?? t.to_location}</td>
                  <td className="px-4 py-3.5">
                    {t.status === 'dispatched'
                      ? <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#fef3c7] text-[#92400e] font-medium">Dispatched</span>
                      : <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] bg-[#dcfce7] text-[#166534] font-medium">Received</span>}
                  </td>
                  <td className="px-4 py-3.5">
                    {t.status === 'dispatched' ? (
                      <button
                        onClick={() => handleConfirm(t.id)}
                        disabled={confirmingId === t.id}
                        className="text-[13px] text-brand-primary hover:underline font-medium disabled:opacity-50"
                      >
                        {confirmingId === t.id ? 'Confirming…' : 'Mark Received'}
                      </button>
                    ) : <span className="text-text-secondary">—</span>}
                  </td>
                </tr>
              ))}
              {!loading && transfers.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-text-secondary text-[14px]">No transfers yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[420px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">New Transfer</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleDispatch} className="flex flex-col gap-4">
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">From location</label>
                <select required value={form.from_location} onChange={e => setForm({...form, from_location: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="">Select…</option>
                  {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">To location</label>
                <select required value={form.to_location} onChange={e => setForm({...form, to_location: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="">Select…</option>
                  {locations.filter(l => l.id !== parseInt(form.from_location)).map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 h-12 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-12 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Dispatching…' : 'Dispatch'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
