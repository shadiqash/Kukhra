import { useEffect, useState } from 'react'
import { getTransfers, updateTransfer } from '../api'

export default function ReceiveTransfer() {
  const [transfers, setTransfers] = useState([])
  const [loading, setLoading] = useState(null)
  const [success, setSuccess] = useState('')

  async function load() {
    getTransfers({ status: 'dispatched' }).then(({ data }) => setTransfers(data.results ?? data)).catch(() => {})
  }
  useEffect(() => { load() }, [])

  async function receive(id) {
    setLoading(id)
    try {
      await updateTransfer(id, { status: 'received' })
      setSuccess('Transfer received')
      await load()
    } finally { setLoading(null) }
  }

  return (
    <div>
      <h1 className="text-lg font-bold text-gray-800 mb-4">Receive Transfer</h1>
      {success && <div className="mb-4 bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg text-sm">{success}</div>}
      <div className="space-y-2">
        {transfers.map((t) => (
          <div key={t.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-3">
            <div className="flex-1">
              <p className="text-sm font-semibold">{t.from_location_name ?? `Location ${t.from_location}`} → {t.to_location_name ?? `Location ${t.to_location}`}</p>
              <p className="text-xs text-gray-500">{new Date(t.dispatched_at).toLocaleDateString()}</p>
            </div>
            <button
              onClick={() => receive(t.id)}
              disabled={loading === t.id}
              className="text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg disabled:opacity-50"
            >
              {loading === t.id ? '…' : 'Receive'}
            </button>
          </div>
        ))}
        {transfers.length === 0 && <p className="text-center text-gray-400 text-sm py-8">No pending transfers</p>}
      </div>
    </div>
  )
}
