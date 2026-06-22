import { useEffect, useState } from 'react'
import { getOrders, getMovements, getLots } from '../api'

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-800">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function Dashboard() {
  const [orders, setOrders] = useState(null)
  const [lots, setLots] = useState(null)

  useEffect(() => {
    getOrders({ page_size: 1 }).then(({ data }) => setOrders(data.count ?? (data.results ?? data).length)).catch(() => {})
    getLots({ page_size: 1 }).then(({ data }) => setLots(data.count ?? (data.results ?? data).length)).catch(() => {})
  }, [])

  return (
    <div>
      <h1 className="text-xl font-bold text-gray-800 mb-6">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Orders" value={orders ?? '—'} sub="All time" />
        <StatCard label="Active Lots" value={lots ?? '—'} sub="In system" />
        <StatCard label="Sales Today" value="—" sub="Coming soon" />
        <StatCard label="Low Stock Alerts" value="—" sub="Check inventory" />
      </div>
    </div>
  )
}
