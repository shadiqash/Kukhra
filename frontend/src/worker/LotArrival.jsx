import { useEffect, useState } from 'react'
import { createLot, getSuppliers, getLocations } from '../api'

export default function LotArrival() {
  const [suppliers, setSuppliers] = useState([])
  const [locations, setLocations] = useState([])
  const [form, setForm] = useState({ code: '', source_type: 'own', supplier: '', arrival_location: '', live_weight_kg: '', bird_count: '' })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getSuppliers(), getLocations()])
      .then(([s, l]) => {
        setSuppliers(s.data.results ?? s.data)
        setLocations((l.data.results ?? l.data).filter((loc) => loc.type !== 'outlet'))
      })
      .catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      const { data } = await createLot({ ...form, supplier: form.supplier || null })
      setSuccess(`Lot ${data.code} recorded`)
      setForm({ code: '', source_type: 'own', supplier: '', arrival_location: '', live_weight_kg: '', bird_count: '' })
    } catch {
      setError('Failed to save lot')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-lg font-bold text-gray-800 mb-4">Lot Arrival</h1>
      {success && <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg text-sm">{success}</div>}
      {error && <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <F label="Lot Code">
          <input value={form.code} onChange={(e) => setForm({...form, code: e.target.value})} required className="inp" />
        </F>
        <F label="Source">
          <select value={form.source_type} onChange={(e) => setForm({...form, source_type: e.target.value})} className="inp">
            <option value="own">Own</option>
            <option value="external">External</option>
          </select>
        </F>
        {form.source_type === 'external' && (
          <F label="Supplier">
            <select value={form.supplier} onChange={(e) => setForm({...form, supplier: e.target.value})} className="inp">
              <option value="">None</option>
              {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </F>
        )}
        <F label="Arrival Location">
          <select value={form.arrival_location} onChange={(e) => setForm({...form, arrival_location: e.target.value})} required className="inp">
            <option value="">Select…</option>
            {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </F>
        <div className="grid grid-cols-2 gap-3">
          <F label="Live Weight (kg)">
            <input type="number" min="0" step="0.1" value={form.live_weight_kg} onChange={(e) => setForm({...form, live_weight_kg: e.target.value})} required className="inp" />
          </F>
          <F label="Bird Count">
            <input type="number" min="0" value={form.bird_count} onChange={(e) => setForm({...form, bird_count: e.target.value})} required className="inp" />
          </F>
        </div>
        <button type="submit" disabled={loading} className="w-full bg-green-600 text-white font-semibold py-2.5 rounded-lg disabled:opacity-50">
          {loading ? 'Saving…' : 'Record Arrival'}
        </button>
      </form>
    </div>
  )
}

function F({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}
