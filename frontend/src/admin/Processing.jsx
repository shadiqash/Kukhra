import { useEffect, useState } from 'react'
import { getProcessingRuns, createProcessingRun, getLots } from '../api'

export default function Processing() {
  const [runs, setRuns] = useState([])
  const [lots, setLots] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ lot: '', input_weight_kg: '', output_weight_kg: '' })
  const [loading, setLoading] = useState(false)

  async function load() {
    const [r, l] = await Promise.all([getProcessingRuns(), getLots({ status: 'slaughter' })])
    setRuns(r.data.results ?? r.data)
    setLots(l.data.results ?? l.data)
  }
  useEffect(() => { load() }, [])

  async function handleSave(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createProcessingRun(form)
      setShowForm(false)
      await load()
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">Processing Runs</h1>
        <button onClick={() => setShowForm(true)} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
          + Run
        </button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Date', 'Lot', 'Input (kg)', 'Output (kg)', 'Yield %', 'Operator'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {runs.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">{new Date(r.run_at).toLocaleDateString()}</td>
                <td className="px-4 py-3 font-mono">{r.lot_code ?? r.lot}</td>
                <td className="px-4 py-3">{r.input_weight_kg}</td>
                <td className="px-4 py-3">{r.output_weight_kg}</td>
                <td className="px-4 py-3">
                  {r.input_weight_kg > 0
                    ? `${((r.output_weight_kg / r.input_weight_kg) * 100).toFixed(1)}%`
                    : '—'}
                </td>
                <td className="px-4 py-3">{r.operator_name ?? r.operator}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No runs</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold mb-4">New Processing Run</h2>
            <form onSubmit={handleSave} className="space-y-3">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Lot</label>
                <select value={form.lot} onChange={(e) => setForm({...form, lot: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">Select lot…</option>
                  {lots.map((l) => <option key={l.id} value={l.id}>{l.code}</option>)}
                </select></div>
              <div className="grid grid-cols-2 gap-3">
                <div><label className="block text-sm font-medium text-gray-700 mb-1">Input (kg)</label>
                  <input type="number" min="0" step="0.1" value={form.input_weight_kg} onChange={(e) => setForm({...form, input_weight_kg: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
                <div><label className="block text-sm font-medium text-gray-700 mb-1">Output (kg)</label>
                  <input type="number" min="0" step="0.1" value={form.output_weight_kg} onChange={(e) => setForm({...form, output_weight_kg: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
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
