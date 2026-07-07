import { useState } from 'react';
import { Save } from 'lucide-react';
import { getTodayBS } from '../utils/formatters';
import { createLot, getSuppliers, getLocations } from '../api';
import { useApi } from '../hooks/useApi';
import { useToast } from '../ui/Toast';
import ErrorBanner from '../ui/ErrorBanner';

export default function LotArrival() {
  const toast = useToast();
  const [form, setForm] = useState({ code: '', source_type: 'external', supplier: '', arrival_location: '', bird_count: '', live_weight_kg: '' });
  const [loading, setLoading] = useState(false);

  const { data: suppliers, loading: suppliersLoading, error: suppliersError, refetch: refetchSuppliers } = useApi(getSuppliers);
  const { data: locations, loading: locationsLoading, error: locationsError, refetch: refetchLocations } = useApi(getLocations);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await createLot({
        code: form.code,
        source_type: form.source_type,
        supplier: form.supplier || null,
        arrival_location: form.arrival_location,
        bird_count: parseInt(form.bird_count),
        live_weight_kg: form.live_weight_kg,
      });
      toast.success('Lot arrived successfully');
      setForm({ code: '', source_type: 'external', supplier: '', arrival_location: '', bird_count: '', live_weight_kg: '' });
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Failed to record arrival');
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      <ErrorBanner error={suppliersError} onRetry={refetchSuppliers} />
      <ErrorBanner error={locationsError} onRetry={refetchLocations} />

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Date (BS)</label>
            <input type="text" value={getTodayBS()} readOnly className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[15px] bg-brand-surface text-text-secondary focus:outline-none" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Lot Code</label>
              <input required type="text" value={form.code} onChange={e => setForm({...form, code: e.target.value})} placeholder="e.g. LOT-2083-001" className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none uppercase" />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Source</label>
              <select value={form.source_type} onChange={e => setForm({...form, source_type: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[15px] focus:border-brand-primary focus:outline-none bg-white">
                <option value="external">External</option>
                <option value="own">Own Farm</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Vendor/Farm</label>
            <select value={form.supplier} onChange={e => setForm({...form, supplier: e.target.value})} disabled={suppliersLoading} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[15px] focus:border-brand-primary focus:outline-none bg-white disabled:opacity-60">
              <option value="">{suppliersLoading ? 'Loading…' : 'None / Own Farm'}</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Arrival Location</label>
            <select required value={form.arrival_location} onChange={e => setForm({...form, arrival_location: e.target.value})} disabled={locationsLoading} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[15px] focus:border-brand-primary focus:outline-none bg-white disabled:opacity-60">
              <option value="">{locationsLoading ? 'Loading…' : 'Select Location…'}</option>
              {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Bird Count (pcs)</label>
              <input required type="number" min="1" value={form.bird_count} onChange={e => setForm({...form, bird_count: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[16px] focus:border-brand-primary focus:outline-none" />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Total Weight (kg)</label>
              <input required type="number" min="0.1" step="0.1" value={form.live_weight_kg} onChange={e => setForm({...form, live_weight_kg: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[16px] focus:border-brand-primary focus:outline-none" />
            </div>
          </div>

          <button type="submit" disabled={loading} className="mt-4 w-full h-12 bg-brand-primary text-white rounded-xl font-sans font-bold text-[16px] flex items-center justify-center gap-2 hover:bg-brand-primaryHover transition-colors disabled:opacity-50 shadow-md">
            <Save size={18} />
            {loading ? 'Saving...' : 'Record Arrival'}
          </button>
        </form>
      </div>
    </div>
  );
}
