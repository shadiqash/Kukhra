import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { createWastage, getProducts, getLocations } from '../api';
import { useApi } from '../hooks/useApi';
import { useToast } from '../ui/Toast';
import ErrorBanner from '../ui/ErrorBanner';

export default function Wastage() {
  const toast = useToast();
  const [form, setForm] = useState({ product: '', qty_kg: '', location: '' });
  const [loading, setLoading] = useState(false);

  const { data: products, loading: productsLoading, error: productsError, refetch: refetchProducts } = useApi(getProducts);
  const { data: locations, loading: locationsLoading, error: locationsError, refetch: refetchLocations } = useApi(getLocations);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await createWastage({
        product: form.product,
        location: form.location,
        qty_kg: form.qty_kg,
      });
      toast.success('Wastage recorded successfully');
      setForm({ product: '', qty_kg: '', location: '' });
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Failed to record wastage');
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      <ErrorBanner error={productsError} onRetry={refetchProducts} />
      <ErrorBanner error={locationsError} onRetry={refetchLocations} />

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Product</label>
            <select required value={form.product} onChange={e => setForm({...form, product: e.target.value})} disabled={productsLoading} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[15px] focus:border-brand-primary focus:outline-none bg-white disabled:opacity-60">
              <option value="">{productsLoading ? 'Loading…' : 'Select Product...'}</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Location</label>
            <select required value={form.location} onChange={e => setForm({...form, location: e.target.value})} disabled={locationsLoading} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[15px] focus:border-brand-primary focus:outline-none bg-white disabled:opacity-60">
              <option value="">{locationsLoading ? 'Loading…' : 'Select Location...'}</option>
              {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Weight (kg)</label>
            <input required type="number" min="0.001" step="0.001" value={form.qty_kg} onChange={e => setForm({...form, qty_kg: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[16px] focus:border-brand-primary focus:outline-none" />
          </div>

          <button type="submit" disabled={loading} className="mt-4 w-full h-12 bg-[#b91c1c] text-white rounded-xl font-sans font-bold text-[16px] flex items-center justify-center gap-2 hover:bg-[#991b1b] transition-colors disabled:opacity-50 shadow-md">
            <Trash2 size={18} />
            {loading ? 'Recording...' : 'Record Wastage'}
          </button>
        </form>
      </div>
    </div>
  );
}
