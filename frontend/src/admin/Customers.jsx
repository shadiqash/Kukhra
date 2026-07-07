import { useState } from 'react';
import { Plus } from 'lucide-react';
import { formatMoney } from '../utils/formatters';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import { getCustomers, createCustomer } from '../api';

export default function Customers() {
  const toast = useToast();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ name: '', type: 'retail', pan: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const { data: customers, loading, error: loadError, refetch } = useApi(getCustomers);

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createCustomer({ name: form.name, type: form.type, pan: form.pan || null });
      setShowModal(false);
      setForm({ name: '', type: 'retail', pan: '' });
      toast.success('Customer saved');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to save customer');
    } finally { setSaving(false); }
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />
      <div className="flex justify-end mb-5 shrink-0">
        <button onClick={() => setShowModal(true)} className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2">
          <Plus size={16} /> Customer
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Name', 'Type', 'PAN', 'Credit Limit', 'Action'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-[#f0f0f0]">
                  {Array.from({ length: 5 }).map((__, j) => <td key={j} className="px-4 py-3.5"><div className="h-4 bg-gray-100 rounded animate-pulse" /></td>)}
                </tr>
              )) : customers.map(c => (
                <tr key={c.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 text-text-primary font-medium">{c.name}</td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium ${c.type === 'wholesale' ? 'bg-[#e0e7ff] text-[#4338ca]' : 'bg-[#f3f4f6] text-[#4b5563]'}`}>
                      {c.type === 'wholesale' ? 'Wholesale' : 'Retail'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-text-secondary text-[13px]">{c.pan || '—'}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">{c.credit_limit_paisa ? formatMoney(c.credit_limit_paisa) : '—'}</td>
                  <td className="px-4 py-3.5">
                    <button className="text-[13px] text-brand-primary hover:underline">View</button>
                  </td>
                </tr>
              ))}
              {!loading && customers.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-text-secondary text-[14px]">No customers yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">Add Customer</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleSave} className="flex flex-col gap-4">
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Name</label>
                <input required type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Type</label>
                <select value={form.type} onChange={e => setForm({...form, type: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="retail">Retail</option>
                  <option value="wholesale">Wholesale</option>
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">PAN Number (Optional)</label>
                <input type="text" value={form.pan} onChange={e => setForm({...form, pan: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
