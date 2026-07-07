import { useState } from 'react';
import { Edit2, Plus } from 'lucide-react';
import NepaliDate from 'nepali-date-converter';
import { formatMoney, formatDateString } from '../utils/formatters';
import { useApi } from '../hooks/useApi';
import ErrorBanner from '../ui/ErrorBanner';
import { useToast } from '../ui/Toast';
import { getProducts, getPrices, createProduct, updateProduct, createPrice } from '../api';

function LoadingRows({ cols }) {
  return Array.from({ length: 4 }).map((_, i) => (
    <tr key={i} className="border-b border-[#f0f0f0]">
      {Array.from({ length: cols }).map((__, j) => (
        <td key={j} className="px-4 py-3.5">
          <div className="h-4 bg-gray-100 rounded animate-pulse w-3/4" />
        </td>
      ))}
    </tr>
  ));
}

export default function Products() {
  const toast = useToast();
  const [showProductModal, setShowProductModal] = useState(false);
  const [showPriceModal, setShowPriceModal] = useState(false);
  const [productForm, setProductForm] = useState({ name: '', barcode: '', uom: 'kg', tax_class: 'exempt' });
  const [editingId, setEditingId] = useState(null);
  const [priceForm, setPriceForm] = useState({ product: '', tier: 'retail', price_paisa_rs: '', valid_from: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const { data: products, loading, error: loadError, refetch } = useApi(getProducts);
  const { data: prices, refetch: refetchPrices } = useApi(getPrices, { active: true });

  // Build price lookup map: product_id → price_paisa (retail)
  const priceMap = {};
  prices.forEach(p => { if (p.tier === 'retail') priceMap[p.product] = p.price_paisa; });
  const wholePriceMap = {};
  prices.forEach(p => { if (p.tier === 'wholesale') wholePriceMap[p.product] = p.price_paisa; });

  async function handleSaveProduct(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      if (editingId) {
        await updateProduct(editingId, productForm);
      } else {
        await createProduct(productForm);
      }
      setShowProductModal(false);
      setEditingId(null);
      setProductForm({ name: '', barcode: '', uom: 'kg', tax_class: 'exempt' });
      toast.success(editingId ? 'Product updated' : 'Product saved');
      refetch();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to save product');
    } finally { setSaving(false); }
  }

  function openEdit(p) {
    setEditingId(p.id);
    setProductForm({ name: p.name, barcode: p.barcode ?? '', uom: p.uom, tax_class: p.tax_class });
    setError('');
    setShowProductModal(true);
  }

  function bsToAD(bsStr) {
    const [y, m, d] = bsStr.split('-').map(Number);
    const nd = new NepaliDate(y, m - 1, d);
    const ad = nd.toJsDate();
    return `${ad.getFullYear()}-${String(ad.getMonth() + 1).padStart(2, '0')}-${String(ad.getDate()).padStart(2, '0')}`;
  }

  async function handleSavePrice(e) {
    e.preventDefault();
    setSaving(true); setError('');
    try {
      await createPrice({
        product: priceForm.product,
        tier: priceForm.tier,
        price_paisa: Math.round(parseFloat(priceForm.price_paisa_rs) * 100),
        valid_from: bsToAD(priceForm.valid_from),
      });
      setShowPriceModal(false);
      setPriceForm({ product: '', tier: 'retail', price_paisa_rs: '', valid_from: '' });
      toast.success('Price saved');
      refetchPrices();
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Failed to save price');
    } finally { setSaving(false); }
  }

  return (
    <div className="max-w-7xl mx-auto h-full flex flex-col">
      <ErrorBanner error={loadError} onRetry={refetch} />
      <div className="flex gap-3 mb-5">
        <button onClick={() => setShowPriceModal(true)} className="h-10 px-4 border-[1.5px] border-brand-primary text-brand-primary rounded-md font-sans text-[14px] hover:bg-[#f0faf8] transition-colors flex items-center gap-2">
          <Plus size={16} /> Price
        </button>
        <button onClick={() => setShowProductModal(true)} className="h-10 px-4 bg-brand-primary text-white rounded-md font-sans font-semibold text-[14px] hover:bg-brand-primaryHover transition-colors flex items-center gap-2">
          <Plus size={16} /> Product
        </button>
      </div>

      <div className="bg-white rounded-xl border-[1.5px] border-brand-border overflow-hidden shadow-sm flex-1 flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left whitespace-nowrap">
            <thead className="bg-brand-surface border-b-[1.5px] border-brand-border sticky top-0 z-10">
              <tr>
                {['Name', 'Barcode', 'UoM', 'Tax', 'Retail Price', 'Wholesale Price', 'Action'].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-[11px] font-sans font-medium text-text-secondary uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? <LoadingRows cols={7} /> : products.map((p) => (
                <tr key={p.id} className="border-b border-[#f0f0f0] hover:bg-[#fafafa] text-[14px]">
                  <td className="px-4 py-3.5 text-text-primary">{p.name}</td>
                  <td className="px-4 py-3.5 text-text-secondary font-mono text-[12px]">{p.barcode || '—'}</td>
                  <td className="px-4 py-3.5 text-text-primary uppercase">{p.uom}</td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium ${p.tax_class === 'exempt' ? 'bg-[#f3f4f6] text-text-secondary' : 'bg-[#fef3c7] text-[#92400e]'}`}>
                      {p.tax_class === 'exempt' ? 'Exempt' : 'Taxable'}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">{priceMap[p.id] ? formatMoney(priceMap[p.id]) : '—'}</td>
                  <td className="px-4 py-3.5 font-mono text-text-primary">{wholePriceMap[p.id] ? formatMoney(wholePriceMap[p.id]) : '—'}</td>
                  <td className="px-4 py-3.5">
                    <button onClick={() => openEdit(p)} aria-label={`Edit ${p.name}`} className="flex items-center justify-center w-8 h-8 rounded border border-brand-border text-text-secondary hover:text-brand-primary hover:border-brand-primary transition-colors">
                      <Edit2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && products.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-10 text-center text-text-secondary text-[14px]">No products yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showProductModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">{editingId ? 'Edit Product' : 'Add Product'}</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleSaveProduct} className="flex flex-col gap-4">
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Name</label>
                <input required type="text" value={productForm.name} onChange={e => setProductForm({...productForm, name: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[15px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Barcode</label>
                <input type="text" value={productForm.barcode} onChange={e => setProductForm({...productForm, barcode: e.target.value})} placeholder="Scan or type…" className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Unit of Measure</label>
                  <select value={productForm.uom} onChange={e => setProductForm({...productForm, uom: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                    <option value="kg">kg</option>
                    <option value="piece">piece</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Tax Class</label>
                  <select value={productForm.tax_class} onChange={e => setProductForm({...productForm, tax_class: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                    <option value="exempt">Exempt</option>
                    <option value="taxable">Taxable (13% VAT)</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => { setShowProductModal(false); setEditingId(null); setProductForm({ name: '', barcode: '', uom: 'kg', tax_class: 'exempt' }); }} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showPriceModal && (
        <div className="fixed inset-0 bg-black/45 flex items-center justify-center z-50 p-4">
          <div className="bg-white w-full max-w-[480px] rounded-[20px] shadow-xl p-7">
            <h2 className="font-sans font-bold text-[20px] text-text-primary mb-5">Add Price</h2>
            {error && <p className="text-brand-danger text-[13px] mb-3">{error}</p>}
            <form onSubmit={handleSavePrice} className="flex flex-col gap-4">
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Product</label>
                <select required value={priceForm.product} onChange={e => setPriceForm({...priceForm, product: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="">Select…</option>
                  {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-medium text-text-secondary mb-1">Tier</label>
                <select value={priceForm.tier} onChange={e => setPriceForm({...priceForm, tier: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 text-[14px] focus:border-brand-primary focus:outline-none bg-white">
                  <option value="retail">Retail</option>
                  <option value="wholesale">Wholesale</option>
                  <option value="member">Member</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Price (Rs)</label>
                  <input required type="number" min="0" step="0.01" value={priceForm.price_paisa_rs} onChange={e => setPriceForm({...priceForm, price_paisa_rs: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[15px] focus:border-brand-primary focus:outline-none" />
                </div>
                <div>
                  <label className="block text-[13px] font-medium text-text-secondary mb-1">Valid From</label>
                  <input required type="text" placeholder="YYYY-MM-DD (BS)" value={priceForm.valid_from} onChange={e => setPriceForm({...priceForm, valid_from: e.target.value})} className="w-full h-11 border-[1.5px] border-brand-border rounded-md px-3 font-mono text-[14px] focus:border-brand-primary focus:outline-none" />
                </div>
              </div>
              <div className="flex gap-3 mt-4">
                <button type="button" onClick={() => setShowPriceModal(false)} className="flex-1 h-11 border-[1.5px] border-brand-border rounded-md text-text-secondary font-medium">Cancel</button>
                <button type="submit" disabled={saving} className="flex-1 h-11 bg-brand-primary text-white rounded-md font-semibold disabled:opacity-50">{saving ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
