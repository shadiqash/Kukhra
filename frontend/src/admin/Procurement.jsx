import { useEffect, useState } from 'react'
import { getPurchaseOrders, createPurchaseOrder, getSuppliers, getGoodsReceived, createGoodsReceived, getLocations } from '../api'

export default function Procurement() {
  const [orders, setOrders] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [locations, setLocations] = useState([])
  const [showPO, setShowPO] = useState(false)
  const [poForm, setPoForm] = useState({ supplier: '', total_paisa: '', status: 'draft' })
  const [loading, setLoading] = useState(false)

  async function load() {
    const [po, s, l] = await Promise.all([getPurchaseOrders(), getSuppliers(), getLocations()])
    setOrders(po.data.results ?? po.data)
    setSuppliers(s.data.results ?? s.data)
    setLocations(l.data.results ?? l.data)
  }
  useEffect(() => { load() }, [])

  async function handleSavePO(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await createPurchaseOrder({ ...poForm, total_paisa: Math.round(parseFloat(poForm.total_paisa) * 100) })
      setShowPO(false)
      await load()
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800">Procurement</h1>
        <button onClick={() => setShowPO(true)} className="text-sm bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700">
          + Purchase Order
        </button>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['ID', 'Supplier', 'Total', 'Status'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {orders.map((o) => (
              <tr key={o.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">#{o.id}</td>
                <td className="px-4 py-3">{o.supplier_name ?? o.supplier}</td>
                <td className="px-4 py-3">Rs {(o.total_paisa / 100).toFixed(2)}</td>
                <td className="px-4 py-3 capitalize">{o.status}</td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No purchase orders</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showPO && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold mb-4">New Purchase Order</h2>
            <form onSubmit={handleSavePO} className="space-y-3">
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Supplier</label>
                <select value={poForm.supplier} onChange={(e) => setPoForm({...poForm, supplier: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  <option value="">Select…</option>
                  {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select></div>
              <div><label className="block text-sm font-medium text-gray-700 mb-1">Total (Rs)</label>
                <input type="number" min="0" step="0.01" value={poForm.total_paisa} onChange={(e) => setPoForm({...poForm, total_paisa: e.target.value})} required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" /></div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={() => setShowPO(false)} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">Cancel</button>
                <button type="submit" disabled={loading} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">{loading ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
