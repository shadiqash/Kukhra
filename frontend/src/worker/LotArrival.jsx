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

      <div className="glass rounded-3xl p-6 shadow-xl border border-border">
        <h2 className="font-sans font-black text-xl text-text-primary mb-6 bg-gradient-to-r from-brand-primary to-[#006e5f] bg-clip-text text-transparent">Log New Arrival</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div>
            <label className="block text-[12px] font-bold text-text-secondary uppercase tracking-wide mb-1.5">Date (BS)</label>
            <input type="text" value={getTodayBS()} readOnly className="w-full h-14 border border-border rounded-xl px-4 font-mono font-bold text-[15px] bg-background/40 text-text-secondary focus:outline-none shadow-sm" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[12px] font-bold text-text-secondary uppercase tracking-wide mb-1.5">Lot Code</label>
              <input required type="text" value={form.code} onChange={e => setForm({...form, code: e.target.value})} placeholder="LOT-2083-001" className="w-full h-14 bg-background/70 border border-border rounded-xl px-4 font-mono font-bold text-[14px] text-text-primary focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 focus:outline-none uppercase shadow-sm transition-all placeholder:text-text-muted placeholder:font-normal" />
            </div>
            <div>
              <label className="block text-[12px] font-bold text-text-secondary uppercase tracking-wide mb-1.5">Source</label>
              <select value={form.source_type} onChange={e => setForm({...form, source_type: e.target.value})} className="w-full h-14 bg-background/70 border border-border rounded-xl px-4 font-bold text-[14px] text-text-primary focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 focus:outline-none shadow-sm transition-all cursor-pointer">
                <option value="external">External</option>
                <option value="own">Own Farm</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-[12px] font-bold text-text-secondary uppercase tracking-wide mb-1.5">Vendor/Farm</label>
            {/* A lot arrival is live birds — only farm-type suppliers are valid
                sources here. Feed/medicine suppliers belong to Procurement's
                purchase orders, not this form. */}
            <select value={form.supplier} onChange={e => setForm({...form, supplier: e.target.value})} disabled={suppliersLoading} className="w-full h-14 bg-background/70 border border-border rounded-xl px-4 font-bold text-[14px] text-text-primary focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 focus:outline-none shadow-sm transition-all disabled:opacity-60 cursor-pointer">
              <option value="">{suppliersLoading ? 'Loading…' : 'None / Own Farm'}</option>
              {suppliers.filter(s => s.type === 'farm').map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[12px] font-bold text-text-secondary uppercase tracking-wide mb-1.5">Arrival Location</label>
            <select required value={form.arrival_location} onChange={e => setForm({...form, arrival_location: e.target.value})} disabled={locationsLoading} className="w-full h-14 bg-background/70 border border-border rounded-xl px-4 font-bold text-[14px] text-text-primary focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 focus:outline-none shadow-sm transition-all disabled:opacity-60 cursor-pointer">
              <option value="">{locationsLoading ? 'Loading…' : 'Select Location…'}</option>
              {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[12px] font-bold text-text-secondary uppercase tracking-wide mb-1.5">Bird Count</label>
              <input required type="number" min="1" value={form.bird_count} onChange={e => setForm({...form, bird_count: e.target.value})} className="w-full h-14 bg-background/70 border border-border rounded-xl px-4 font-mono font-black text-lg text-text-primary focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 focus:outline-none shadow-sm transition-all" />
            </div>
            <div>
              <label className="block text-[12px] font-bold text-text-secondary uppercase tracking-wide mb-1.5">Total Wt (kg)</label>
              <input required type="number" min="0.1" step="0.1" value={form.live_weight_kg} onChange={e => setForm({...form, live_weight_kg: e.target.value})} className="w-full h-14 bg-background/70 border border-border rounded-xl px-4 font-mono font-black text-lg text-text-primary focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 focus:outline-none shadow-sm transition-all" />
            </div>
          </div>

          <button type="submit" disabled={loading} className="mt-6 w-full h-14 bg-gradient-to-r from-brand-primary to-brand-primaryHover text-white rounded-2xl font-sans font-black text-[18px] flex items-center justify-center gap-2 hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 shadow-md">
            <Save size={20} />
            {loading ? 'Saving...' : 'Record Arrival'}
          </button>
        </form>
      </div>
    </div>
  );
}
