import { useState, useMemo } from 'react';
import { PackageCheck, AlertCircle } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getTransfers, getLocations, confirmTransferReceipt } from '../api';
import { formatDateString } from '../utils/formatters';

export default function ReceiveTransfer() {
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const { data: transfers, refetch } = useApi(getTransfers, { status: 'dispatched' });
  const { data: locations } = useApi(getLocations);

  const locationMap = useMemo(
    () => Object.fromEntries(locations.map(l => [l.id, l])),
    [locations],
  );

  const selected = transfers.find(t => String(t.id) === selectedId);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedId) return;
    setLoading(true); setError('');
    try {
      await confirmTransferReceipt(selectedId);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      setSelectedId('');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to confirm receipt');
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      {success && (
        <div className="bg-[#dcfce7] border-[1.5px] border-[#166534] text-[#166534] px-4 py-3 rounded-xl text-[14px] font-medium flex items-center justify-center">
          Transfer Received Successfully!
        </div>
      )}
      {error && (
        <div className="bg-[#fee2e2] border-[1.5px] border-[#b91c1c] text-[#b91c1c] px-4 py-3 rounded-xl text-[14px] font-medium flex items-center justify-center">
          {error}
        </div>
      )}

      {transfers.length === 0 ? (
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-8 shadow-sm flex flex-col items-center text-center">
          <div className="w-16 h-16 bg-[#f0faf8] text-brand-primary rounded-full flex items-center justify-center mb-4">
            <PackageCheck size={32} />
          </div>
          <h3 className="font-sans font-bold text-[18px] text-text-primary mb-2">No Pending Transfers</h3>
          <p className="text-[14px] text-text-secondary">You have received all dispatched items.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm">
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Select Incoming Transfer</label>
              <select required value={selectedId} onChange={e => setSelectedId(e.target.value)} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                <option value="">Select Transfer...</option>
                {transfers.map(t => (
                  <option key={t.id} value={t.id}>#{t.id} — from {locationMap[t.from_location]?.name ?? t.from_location}</option>
                ))}
              </select>
            </div>

            {selected && (
              <div className="bg-brand-surface rounded-xl p-4 border border-brand-border flex flex-col gap-2">
                <div className="flex items-start gap-2">
                  <AlertCircle size={16} className="text-brand-secondary mt-0.5" />
                  <div>
                    <h4 className="font-sans font-bold text-[14px] text-text-primary">Transfer Details</h4>
                    <p className="text-[13px] text-text-secondary mt-1">
                      From: {locationMap[selected.from_location]?.name ?? selected.from_location}
                    </p>
                    <p className="text-[12px] text-text-secondary mt-0.5">
                      Dispatched: {selected.dispatched_at ? formatDateString(new Date(selected.dispatched_at)) : '—'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <button type="submit" disabled={loading || !selectedId} className="mt-2 w-full h-12 bg-brand-primary text-white rounded-xl font-sans font-bold text-[16px] flex items-center justify-center gap-2 hover:bg-brand-primaryHover transition-colors disabled:opacity-50 shadow-md">
              <PackageCheck size={18} />
              {loading ? 'Confirming...' : 'Confirm Receipt'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
