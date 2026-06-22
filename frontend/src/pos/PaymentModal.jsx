import { useState } from 'react'
import { createOrder, createOrderLine, createPayment } from '../api'
import { cachePendingOrder } from './offline/db'

const METHODS = ['cash', 'card', 'esewa', 'khalti']

export default function PaymentModal({ lines, session, locationId, onSuccess, onCancel }) {
  const total = lines.reduce((s, l) => s + l.line_total_paisa, 0)
  const [method, setMethod] = useState('cash')
  const [ref, setRef] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit() {
    setLoading(true)
    setError('')
    try {
      const order = {
        fulfilled_location: locationId,
        session: session?.id ?? null,
        source: 'counter',
        status: 'completed',
        total_paisa: total,
      }

      if (!navigator.onLine) {
        await cachePendingOrder({ order, lines, payment: { method, ref, amount_paisa: total } })
        onSuccess({ offline: true })
        return
      }

      const { data: createdOrder } = await createOrder(order)
      await Promise.all(
        lines.map((l) =>
          createOrderLine({
            order: createdOrder.id,
            product: l.product_id,
            price: l.price_id,
            qty_kg: l.uom === 'kg' ? l.qty : 0,
            qty_pieces: l.uom === 'piece' ? l.qty : 0,
            line_total_paisa: l.line_total_paisa,
          })
        )
      )
      await createPayment({
        order: createdOrder.id,
        method,
        amount_paisa: total,
        ref: ref || null,
      })
      onSuccess({ order: createdOrder })
    } catch {
      setError('Payment failed. Check connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h2 className="text-lg font-bold mb-4">Payment</h2>
        <p className="text-3xl font-bold text-green-700 text-center mb-6">
          Rs {(total / 100).toFixed(2)}
        </p>
        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
        {!navigator.onLine && (
          <p className="text-amber-600 text-xs mb-3 bg-amber-50 rounded px-3 py-2">
            Offline — order will be queued and synced when connection restores.
          </p>
        )}
        <div className="grid grid-cols-2 gap-2 mb-4">
          {METHODS.map((m) => (
            <button
              key={m}
              onClick={() => setMethod(m)}
              className={`py-2 rounded-lg text-sm font-medium border transition ${
                method === m
                  ? 'bg-green-600 text-white border-green-600'
                  : 'border-gray-200 text-gray-700 hover:border-green-400'
              }`}
            >
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>
        {method !== 'cash' && (
          <input
            type="text"
            placeholder="Reference / transaction ID"
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        )}
        <div className="flex gap-2">
          <button onClick={onCancel} className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-lg text-sm">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={loading}
            className="flex-1 bg-green-600 text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
          >
            {loading ? 'Processing…' : 'Confirm Payment'}
          </button>
        </div>
      </div>
    </div>
  )
}
