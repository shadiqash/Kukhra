import { useEffect, useState } from 'react'
import { createWastage, getProducts, getLocations, getLots } from '../api'

export default function Wastage() {
  const [products, setProducts] = useState([])
  const [locations, setLocations] = useState([])
  const [lots, setLots] = useState([])
  const [form, setForm] = useState({ product: '', location: '', lot: '', qty_kg: '', reason: '' })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getProducts(), getLocations(), getLots()])
      .then(([p, l, lo]) => {
        setProducts(p.data.results ?? p.data)
        setLocations(l.data.results ?? l.data)
        setLots(lo.data.results ?? lo.data)
      })
      .catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      await createWastage({
        product: form.product,
        location: form.location,
        lot: form.lot || null,
        qty_kg: -Math.abs(parseFloat(form.qty_kg)),
        qty_pieces: 0,
        ref_id: null,
      })
      setSuccess('Wastage recorded')
      setForm({ product: '', location: '', lot: '', qty_kg: '', reason: '' })
    } catch {
      setError('Failed to record wastage')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <h1 className="text-lg font-bold text-gray-800 mb-4">Record Wastage</h1>
      {success && <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg text-sm">{success}</div>}
      {error && <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Product</label>
          <select value={form.product} onChange={(e) => setForm({...form, product: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">Select…</option>
            {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
          <select value={form.location} onChange={(e) => setForm({...form, location: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">Select…</option>
            {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Lot (optional)</label>
          <select value={form.lot} onChange={(e) => setForm({...form, lot: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">None</option>
            {lots.map((l) => <option key={l.id} value={l.id}>{l.code}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Quantity (kg)</label>
          <input type="number" min="0.01" step="0.01" value={form.qty_kg} onChange={(e) => setForm({...form, qty_kg: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
        </div>
        <button type="submit" disabled={loading} className="w-full bg-red-600 text-white font-semibold py-2.5 rounded-lg disabled:opacity-50">
          {loading ? 'Saving…' : 'Record Wastage'}
        </button>
      </form>
    </div>
  )
}
