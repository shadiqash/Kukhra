import { useEffect, useState } from 'react'
import { createProcessingRun, getLots } from '../api'

export default function ProcessingEntry() {
  const [lots, setLots] = useState([])
  const [form, setForm] = useState({ lot: '', input_weight_kg: '', output_weight_kg: '' })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    getLots({ status: 'slaughter' }).then(({ data }) => setLots(data.results ?? data)).catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      await createProcessingRun(form)
      setSuccess('Processing run recorded')
      setForm({ lot: '', input_weight_kg: '', output_weight_kg: '' })
    } catch {
      setError('Failed to save run')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <h1 className="text-lg font-bold text-gray-800 mb-4">Processing Entry</h1>
      {success && <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg text-sm">{success}</div>}
      {error && <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">{error}</div>}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Lot</label>
          <select value={form.lot} onChange={(e) => setForm({...form, lot: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
            <option value="">Select lot…</option>
            {lots.map((l) => <option key={l.id} value={l.id}>{l.code} ({l.live_weight_kg} kg)</option>)}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Input (kg)</label>
            <input type="number" min="0" step="0.1" value={form.input_weight_kg} onChange={(e) => setForm({...form, input_weight_kg: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Output (kg)</label>
            <input type="number" min="0" step="0.1" value={form.output_weight_kg} onChange={(e) => setForm({...form, output_weight_kg: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        {form.input_weight_kg && form.output_weight_kg && (
          <p className="text-sm text-gray-500">
            Yield: {((parseFloat(form.output_weight_kg) / parseFloat(form.input_weight_kg)) * 100).toFixed(1)}%
          </p>
        )}
        <button type="submit" disabled={loading} className="w-full bg-green-600 text-white font-semibold py-2.5 rounded-lg disabled:opacity-50">
          {loading ? 'Saving…' : 'Record Run'}
        </button>
      </form>
    </div>
  )
}
