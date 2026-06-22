import { useEffect, useState } from 'react'
import { getMovements, getLocations } from '../api'

const TYPE_COLORS = {
  production: 'text-green-600',
  transfer: 'text-blue-600',
  sale: 'text-orange-600',
  return: 'text-purple-600',
  wastage: 'text-red-600',
  adjustment: 'text-gray-600',
}

export default function Inventory() {
  const [movements, setMovements] = useState([])
  const [locations, setLocations] = useState([])
  const [locFilter, setLocFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  useEffect(() => {
    getLocations().then(({ data }) => setLocations(data.results ?? data)).catch(() => {})
  }, [])

  useEffect(() => {
    const params = {}
    if (locFilter) params.location = locFilter
    if (typeFilter) params.type = typeFilter
    getMovements(params).then(({ data }) => setMovements(data.results ?? data)).catch(() => {})
  }, [locFilter, typeFilter])

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-6">Inventory Movements</h1>
      <div className="flex gap-3 mb-4">
        <select value={locFilter} onChange={(e) => setLocFilter(e.target.value)} className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm">
          <option value="">All Locations</option>
          {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm">
          <option value="">All Types</option>
          {Object.keys(TYPE_COLORS).map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Date', 'Type', 'Product', 'Location', 'Qty (kg)', 'Qty (pcs)', 'Lot'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {movements.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">{new Date(m.created_at).toLocaleDateString()}</td>
                <td className={`px-4 py-3 font-medium capitalize ${TYPE_COLORS[m.type] || ''}`}>{m.type}</td>
                <td className="px-4 py-3">{m.product_name ?? m.product}</td>
                <td className="px-4 py-3">{m.location_name ?? m.location}</td>
                <td className="px-4 py-3">{m.qty_kg}</td>
                <td className="px-4 py-3">{m.qty_pieces}</td>
                <td className="px-4 py-3 text-gray-500">{m.lot ?? '—'}</td>
              </tr>
            ))}
            {movements.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No movements</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
