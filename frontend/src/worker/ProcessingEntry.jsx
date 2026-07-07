import { useState } from 'react';
import { Save } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { getLots, createProcessingRun } from '../api';
import { useToast } from '../ui/Toast';
import ErrorBanner from '../ui/ErrorBanner';

export default function ProcessingEntry() {
  const toast = useToast();
  const [form, setForm] = useState({ lot: '', input_weight_kg: '', output_weight_kg: '' });
  const [loading, setLoading] = useState(false);

  const { data: lots, loading: lotsLoading, error: lotsError, refetch: refetchLots } = useApi(getLots, { status: 'active' });

  const inputKg = parseFloat(form.input_weight_kg) || 0;
  const outputKg = parseFloat(form.output_weight_kg) || 0;
  const wastageKg = inputKg > 0 ? Math.max(0, inputKg - outputKg) : 0;
  const yieldPct = inputKg > 0 ? ((outputKg / inputKg) * 100).toFixed(1) : '0.0';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await createProcessingRun({
        lot: form.lot,
        input_weight_kg: form.input_weight_kg,
        output_weight_kg: form.output_weight_kg,
      });
      toast.success('Processing data saved');
      setForm({ lot: '', input_weight_kg: '', output_weight_kg: '' });
    } catch (err) {
      toast.error(err?.response?.data?.detail ?? 'Failed to save processing record');
    } finally { setLoading(false); }
  };

  return (
    <div className="flex flex-col gap-4">
      <ErrorBanner error={lotsError} onRetry={refetchLots} />

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border p-5 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div>
            <label className="block text-[13px] font-medium text-text-secondary mb-1">Active Lot</label>
            <select required value={form.lot} onChange={e => setForm({...form, lot: e.target.value})} disabled={lotsLoading} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[15px] focus:border-brand-primary focus:outline-none bg-white disabled:opacity-60">
              <option value="">{lotsLoading ? 'Loading…' : 'Select Lot...'}</option>
              {lots.map(l => <option key={l.id} value={l.id}>{l.code}</option>)}
            </select>
          </div>

          <div className="space-y-4 pt-2 border-t-[1.5px] border-dashed border-brand-border">
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Live Weight Used (kg)</label>
              <input required type="number" min="0.1" step="0.001" value={form.input_weight_kg} onChange={e => setForm({...form, input_weight_kg: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[16px] focus:border-brand-primary focus:outline-none" />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-text-secondary mb-1">Dressed Weight (kg)</label>
              <input required type="number" min="0.1" step="0.001" value={form.output_weight_kg} onChange={e => setForm({...form, output_weight_kg: e.target.value})} className="w-full h-12 border-[1.5px] border-brand-border rounded-lg px-3 font-mono text-[16px] focus:border-brand-primary focus:outline-none" />
            </div>
          </div>

          <div className="bg-[#f0faf8] rounded-xl p-4 border border-[#ccfbf1]">
            <div className="flex justify-between items-start">
              <div>
                <div className="text-[12px] text-text-secondary font-medium">Calculated Yield</div>
                <div className={`font-mono text-[24px] font-bold ${parseFloat(yieldPct) >= 70 ? 'text-brand-success' : 'text-brand-danger'}`}>
                  {yieldPct}%
                </div>
              </div>
              <div className="text-right">
                <div className="text-[12px] text-text-secondary font-medium">Wastage</div>
                <div className="font-mono text-[18px] font-bold text-brand-danger">{wastageKg.toFixed(3)} kg</div>
              </div>
            </div>
            <div className="text-right text-[11px] text-text-secondary mt-1">Target: ~70–72%</div>
          </div>

          <button type="submit" disabled={loading} className="mt-4 w-full h-12 bg-brand-primary text-white rounded-xl font-sans font-bold text-[16px] flex items-center justify-center gap-2 hover:bg-brand-primaryHover transition-colors disabled:opacity-50 shadow-md">
            <Save size={18} />
            {loading ? 'Saving...' : 'Save Processing Record'}
          </button>
        </form>
      </div>
    </div>
  );
}
