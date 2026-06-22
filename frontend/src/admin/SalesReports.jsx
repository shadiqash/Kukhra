import { useEffect, useState } from 'react'
import { getOrders } from '../api'

export default function SalesReports() {
  const [orders, setOrders] = useState([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    const params = {}
    if (dateFrom) params.created_at__gte = dateFrom
    if (dateTo) params.created_at__lte = dateTo
    getOrders(params).then(({ data }) => setOrders(data.results ?? data)).catch(() => {})
  }, [dateFrom, dateTo])

  const totalRevenue = orders.reduce((s, o) => s + o.total_paisa, 0)

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-6">Sales Reports</h1>
      <div className="flex gap-3 mb-6 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">From</label>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">To</label>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-xs text-gray-500 mb-1">Total Orders</p>
          <p className="text-2xl font-bold">{orders.length}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <p className="text-xs text-gray-500 mb-1">Revenue</p>
          <p className="text-2xl font-bold text-green-700">Rs {(totalRevenue / 100).toFixed(2)}</p>
        </div>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Order ID', 'Date', 'Source', 'Status', 'Total'].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {orders.map((o) => (
              <tr key={o.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-gray-500">#{o.id}</td>
                <td className="px-4 py-3 text-gray-500">{new Date(o.created_at ?? o.id).toLocaleDateString()}</td>
                <td className="px-4 py-3 capitalize">{o.source}</td>
                <td className="px-4 py-3 capitalize">{o.status}</td>
                <td className="px-4 py-3 font-medium">Rs {(o.total_paisa / 100).toFixed(2)}</td>
              </tr>
            ))}
            {orders.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No orders in range</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
