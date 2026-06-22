import { useEffect, useState } from 'react'
import { getLots, updateLot } from '../api'

const STATUSES = ['arrival', 'grading', 'storage', 'slaughter', 'packaging', 'sale', 'settlement']

export default function FlockLog() {
  const [lots, setLots] = useState([])
  const [selected, setSelected] = useState(null)
  const [nextStatus, setNextStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')

  async function load() {
    getLots().then(({ data }) => setLots(data.results ?? data)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  async function handleUpdate(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await updateLot(selected.id, { status: nextStatus })
      setSuccess(`Lot ${selected.code} updated to ${nextStatus}`)
      setSelected(null)
      await load()
    } finally { setLoading(false) }
  }

  return (
    <div>
      <h1 className="text-lg font-bold text-gray-800 mb-4">Flock Log</h1>
      {success && <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg text-sm">{success}</div>}
      <div className="space-y-2">
        {lots.map((lot) => (
          <div key={lot.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className="flex-1">
              <p className="font-mono font-semibold">{lot.code}</p>
              <p className="text-xs text-gray-500 capitalize">{lot.status} · {lot.bird_count} birds · {lot.live_weight_kg} kg</p>
            </div>
            <button
              onClick={() => { setSelected(lot); setNextStatus(lot.status) }}
              className="text-xs border border-gray-200 px-3 py-1 rounded-lg hover:border-green-400"
            >
              Update
            </button>
          </div>
        ))}
        {lots.length === 0 && <p className="text-center text-gray-400 text-sm py-8">No lots</p>}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="font-bold text-lg mb-4">Update Lot {selected.code}</h2>
            <form onSubmit={handleUpdate} className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select value={nextStatus} onChange={(e) => setNextStatus(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setSelected(null)} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">Cancel</button>
                <button type="submit" disabled={loading} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">{loading ? 'Saving…' : 'Update'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
