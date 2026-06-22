import { useEffect, useState } from 'react'
import { getTransfers, createTransfer, updateTransfer, getLocations } from '../api'

const STATUS_COLORS = {
  dispatched: 'bg-yellow-100 text-yellow-700',
  received: 'bg-green-100 text-green-700',
}

export default function Transfers() {
  const [transfers, setTransfers] = useState([])
  const [locations, setLocations] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ from_location: '', to_location: '' })
  const [loading, setLoading] = useState(false)

  async function load() {
    const [t, l] = await Promise.all([getTransfers(), getLocations()])
    setTransfers(t.data.results ?? t.data)
    setLocations(l.data.results ?? l.data)
  }
  useEffect(() => { load() }, [])

  async function handleSave(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createTransfer({ ...form, status: 'dispatched', dispatched_at: new Date().toISOString() })
      setShowForm(false)
      await load()
    } finally { setLoading(false) }
  }

  async function markReceived(id) {
    await updateTransfer(id, { status: 'received' })
    await load()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">Stock Transfers</h1>
        <button onClick={() => setShowForm(true)} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
          + Transfer
        </button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Date', 'From', 'To', 'Status', ''].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {transfers.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">{new Date(t.dispatched_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">{t.from_location_name ?? t.from_location}</td>
                <td className="px-4 py-3">{t.to_location_name ?? t.to_location}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[t.status] || ''}`}>
                    {t.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {t.status === 'dispatched' && (
                    <button onClick={() => markReceived(t.id)} className="text-xs text-blue-600 hover:underline">
                      Mark Received
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {transfers.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No transfers</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold mb-4">New Transfer</h2>
            <form onSubmit={handleSave} className="space-y-3">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">From</label>
                <select value={form.from_location} onChange={(e) => setForm({...form, from_location: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">Select…</option>
                  {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">To</label>
                <select value={form.to_location} onChange={(e) => setForm({...form, to_location: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">Select…</option>
                  {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select></div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowForm(false)} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">Cancel</button>
                <button type="submit" disabled={loading} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">{loading ? 'Saving…' : 'Dispatch'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
