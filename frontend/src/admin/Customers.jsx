import { useEffect, useState } from 'react'
import { getCustomers, createCustomer } from '../api'

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', type: 'retail', pan: '', credit_limit_paisa: '0' })
  const [loading, setLoading] = useState(false)

  async function load() {
    const { data } = await getCustomers()
    setCustomers(data.results ?? data)
  }
  useEffect(() => { load() }, [])

  async function handleSave(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createCustomer({
        ...form,
        pan: form.pan || null,
        credit_limit_paisa: Math.round(parseFloat(form.credit_limit_paisa) * 100),
      })
      setShowForm(false)
      await load()
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">Customers</h1>
        <button onClick={() => setShowForm(true)} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
          + Customer
        </button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Name', 'Type', 'PAN', 'Credit Limit'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {customers.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{c.name}</td>
                <td className="px-4 py-3 capitalize">{c.type}</td>
                <td className="px-4 py-3 text-gray-500">{c.pan || '—'}</td>
                <td className="px-4 py-3">Rs {(c.credit_limit_paisa / 100).toFixed(2)}</td>
              </tr>
            ))}
            {customers.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No customers</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold mb-4">New Customer</h2>
            <form onSubmit={handleSave} className="space-y-3">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select value={form.type} onChange={(e) => setForm({...form, type: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="retail">Retail</option>
                  <option value="wholesale">Wholesale</option>
                </select></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">PAN (optional)</label>
                <input value={form.pan} onChange={(e) => setForm({...form, pan: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Credit Limit (Rs)</label>
                <input type="number" min="0" step="0.01" value={form.credit_limit_paisa} onChange={(e) => setForm({...form, credit_limit_paisa: e.target.value})} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
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
