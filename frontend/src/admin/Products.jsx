import { useEffect, useState } from 'react'
import { getProducts, createProduct, updateProduct, getPrices, createPrice } from '../api'

export default function Products() {
  const [products, setProducts] = useState([])
  const [prices, setPrices] = useState({})
  const [form, setForm] = useState({ name: '', barcode: '', uom: 'kg', is_weighed: true, tax_class: 'exempt' })
  const [priceForm, setPriceForm] = useState({ product: '', tier: 'retail', price_paisa: '', valid_from: '' })
  const [showForm, setShowForm] = useState(false)
  const [showPriceForm, setShowPriceForm] = useState(false)
  const [loading, setLoading] = useState(false)

  async function load() {
    const [pr, pc] = await Promise.all([getProducts(), getPrices({ valid_to__isnull: true })])
    setProducts(pr.data.results ?? pr.data)
    const map = {}
    ;(pc.data.results ?? pc.data).forEach((p) => { map[p.product] = p })
    setPrices(map)
  }
  useEffect(() => { load() }, [])

  async function handleSaveProduct(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createProduct(form)
      setForm({ name: '', barcode: '', uom: 'kg', is_weighed: true, tax_class: 'exempt' })
      setShowForm(false)
      await load()
    } finally { setLoading(false) }
  }

  async function handleSavePrice(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createPrice({ ...priceForm, price_paisa: Math.round(parseFloat(priceForm.price_paisa) * 100) })
      setShowPriceForm(false)
      await load()
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">Products</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowPriceForm(true)} className="text-sm border border-gray-300 px-3 py-1.5 rounded-lg hover:bg-gray-50">
            + Price
          </button>
          <button onClick={() => setShowForm(true)} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
            + Product
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Name', 'Barcode', 'UoM', 'Weighed', 'Tax', 'Retail Price'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {products.map((p) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{p.name}</td>
                <td className="px-4 py-3 text-gray-500">{p.barcode || '—'}</td>
                <td className="px-4 py-3">{p.uom}</td>
                <td className="px-4 py-3">{p.is_weighed ? 'Yes' : 'No'}</td>
                <td className="px-4 py-3">{p.tax_class}</td>
                <td className="px-4 py-3">
                  {prices[p.id] ? `Rs ${(prices[p.id].price_paisa / 100).toFixed(2)}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <Modal title="Add Product" onClose={() => setShowForm(false)}>
          <form onSubmit={handleSaveProduct} className="space-y-3">
            <Field label="Name"><input value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} required className="input" /></Field>
            <Field label="Barcode (optional)"><input value={form.barcode} onChange={(e) => setForm({...form, barcode: e.target.value})} className="input" /></Field>
            <Field label="UoM">
              <select value={form.uom} onChange={(e) => setForm({...form, uom: e.target.value})} className="input">
                <option value="kg">kg</option>
                <option value="piece">piece</option>
              </select>
            </Field>
            <Field label="Tax Class">
              <select value={form.tax_class} onChange={(e) => setForm({...form, tax_class: e.target.value})} className="input">
                <option value="exempt">Exempt</option>
                <option value="taxable">Taxable (13% VAT)</option>
              </select>
            </Field>
            <ModalActions onCancel={() => setShowForm(false)} loading={loading} />
          </form>
        </Modal>
      )}

      {showPriceForm && (
        <Modal title="Add Price" onClose={() => setShowPriceForm(false)}>
          <form onSubmit={handleSavePrice} className="space-y-3">
            <Field label="Product">
              <select value={priceForm.product} onChange={(e) => setPriceForm({...priceForm, product: e.target.value})} required className="input">
                <option value="">Select…</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
            <Field label="Tier">
              <select value={priceForm.tier} onChange={(e) => setPriceForm({...priceForm, tier: e.target.value})} className="input">
                <option value="retail">Retail</option>
                <option value="wholesale">Wholesale</option>
                <option value="member">Member</option>
              </select>
            </Field>
            <Field label="Price (Rs)"><input type="number" min="0" step="0.01" value={priceForm.price_paisa} onChange={(e) => setPriceForm({...priceForm, price_paisa: e.target.value})} required className="input" /></Field>
            <Field label="Valid From"><input type="date" value={priceForm.valid_from} onChange={(e) => setPriceForm({...priceForm, valid_from: e.target.value})} required className="input" /></Field>
            <ModalActions onCancel={() => setShowPriceForm(false)} loading={loading} />
          </form>
        </Modal>
      )}
    </div>
  )
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-bold mb-4">{title}</h2>
        {children}
      </div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}

function ModalActions({ onCancel, loading }) {
  return (
    <div className="flex gap-2 pt-2">
      <button type="button" onClick={onCancel} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">Cancel</button>
      <button type="submit" disabled={loading} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">
        {loading ? 'Saving…' : 'Save'}
      </button>
    </div>
  )
}
