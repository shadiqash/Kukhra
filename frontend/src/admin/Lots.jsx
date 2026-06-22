import { useEffect, useState } from 'react'
import { getLots, createLot, updateLot, getSuppliers, getLocations } from '../api'

const STATUS_COLORS = {
  arrival: 'bg-blue-100 text-blue-700',
  grading: 'bg-yellow-100 text-yellow-700',
  storage: 'bg-gray-100 text-gray-700',
  slaughter: 'bg-red-100 text-red-700',
  packaging: 'bg-purple-100 text-purple-700',
  sale: 'bg-green-100 text-green-700',
  settlement: 'bg-emerald-100 text-emerald-700',
}

export default function Lots() {
  const [lots, setLots] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [locations, setLocations] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ code: '', source_type: 'own', supplier: '', arrival_location: '', live_weight_kg: '', bird_count: '' })
  const [loading, setLoading] = useState(false)

  async function load() {
    const [l, s, loc] = await Promise.all([getLots(), getSuppliers(), getLocations()])
    setLots(l.data.results ?? l.data)
    setSuppliers(s.data.results ?? s.data)
    setLocations(loc.data.results ?? loc.data)
  }
  useEffect(() => { load() }, [])

  async function handleSave(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createLot({ ...form, supplier: form.supplier || null })
      setShowForm(false)
      await load()
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">Lots</h1>
        <button onClick={() => setShowForm(true)} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
          + Lot
        </button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Code', 'Source', 'Location', 'Birds', 'Weight (kg)', 'Status'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {lots.map((l) => (
              <tr key={l.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono font-medium">{l.code}</td>
                <td className="px-4 py-3 capitalize">{l.source_type}</td>
                <td className="px-4 py-3">{l.arrival_location_name ?? l.arrival_location}</td>
                <td className="px-4 py-3">{l.bird_count}</td>
                <td className="px-4 py-3">{l.live_weight_kg}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[l.status] || 'bg-gray-100 text-gray-600'}`}>
                    {l.status}
                  </span>
                </td>
              </tr>
            ))}
            {lots.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No lots</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold mb-4">New Lot</h2>
            <form onSubmit={handleSave} className="space-y-3">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Lot Code</label>
                <input value={form.code} onChange={(e) => setForm({...form, code: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
                <select value={form.source_type} onChange={(e) => setForm({...form, source_type: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="own">Own</option>
                  <option value="external">External</option>
                </select></div>
              {form.source_type === 'external' && (
                <div><label className="block text-sm font-medium text-gray-700 mb-1">Supplier</label>
                  <select value={form.supplier} onChange={(e) => setForm({...form, supplier: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                    <option value="">None</option>
                    {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select></div>
              )}
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Arrival Location</label>
                <select value={form.arrival_location} onChange={(e) => setForm({...form, arrival_location: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">Select…</option>
                  {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="block text-sm font-medium text-gray-700 mb-1">Live Weight (kg)</label>
                  <input type="number" min="0" step="0.1" value={form.live_weight_kg} onChange={(e) => setForm({...form, live_weight_kg: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
                <div><label className="block text-sm font-medium text-gray-700 mb-1">Bird Count</label>
                  <input type="number" min="0" value={form.bird_count} onChange={(e) => setForm({...form, bird_count: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">Cancel</button>
                <button type="submit" disabled={loading} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">{loading ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
