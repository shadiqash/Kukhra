import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { createWastage, getProducts, getLocations } from '../api';
import { useApi } from '../hooks/useApi';

export default function Wastage() {
  const [form, setForm] = useState({ product: '', qty_kg: '', location: '' });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const { data: products } = useApi(getProducts);
  const { data: locations } = useApi(getLocations);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await createWastage({
        product: form.product,
        location: form.location,
        qty_kg: form.qty_kg,
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      setForm({ product: '', qty_kg: '', location: '' });
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to record wastage');
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      {success && (
        <div className="bg-[#dcfce7] border-[1.5px] border-[#166534] text-[#166534] px-4 py-3 rounded-xl text-[14px] font-medium flex items-center justify-center">
          Wastage Recorded Successfully!
        </div>
      )}
      {error && (
        <div className="bg-[#fee2e2] border-[1.5px] border-[#b91c1c] text-[#b91c1c] px-4 py-3 rounded-xl text-[14px] font-medium flex items-center justify-center">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Product</label>
            <select required value={form.product} onChange={e => setForm({...form, product: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[15px] focus:border-brand-primary focus:outline-none bg-white">
              <option value="">Select Product...</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Location</label>
            <select required value={form.location} onChange={e => setForm({...form, location: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 text-[15px] focus:border-brand-primary focus:outline-none bg-white">
              <option value="">Select Location...</option>
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
