import { useState } from 'react'
import { openSession, closeSession } from '../api'

export default function ShiftModal({ session, counterId, onOpen, onClose, onDismiss }) {
  const [float, setFloat] = useState('')
  const [counted, setCounted] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleOpen(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data } = await openSession({
        counter: counterId,
        opening_float_paisa: Math.round(parseFloat(float) * 100),
      })
      onOpen(data)
    } catch {
      setError('Failed to open shift')
    } finally {
      setLoading(false)
    }
  }

  async function handleClose(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data } = await closeSession(session.id, {
        closing_counted_paisa: Math.round(parseFloat(counted) * 100),
      })
      onClose(data)
    } catch {
      setError('Failed to close shift')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        {!session ? (
          <>
            <h2 className="text-lg font-bold mb-4">Open Shift</h2>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <form onSubmit={handleOpen} className="space-y-3">
              <div>
                <label className="text-sm font-medium text-gray-700">Opening Float (Rs)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={float}
                  onChange={(e) => setFloat(e.target.value)}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mt-1 focus:ring-2 focus:ring-green-500 focus:outline-none"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={onDismiss} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">
                  {loading ? 'Opening…' : 'Open Shift'}
                </button>
              </div>
            </form>
          </>
        ) : (
          <>
            <h2 className="text-lg font-bold mb-1">Close Shift</h2>
            <p className="text-sm text-gray-500 mb-4">
              Float opened: Rs {(session.opening_float_paisa / 100).toFixed(2)}
            </p>
            {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
            <form onSubmit={handleClose} className="space-y-3">
              <div>
                <label className="text-sm font-medium text-gray-700">Counted Cash (Rs)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={counted}
                  onChange={(e) => setCounted(e.target.value)}
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mt-1 focus:ring-2 focus:ring-green-500 focus:outline-none"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="button" onClick={onDismiss} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50">
                  {loading ? 'Closing…' : 'Close Shift'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
