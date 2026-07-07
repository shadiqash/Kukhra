import { useRef, useState } from 'react'
import { createOrder, createOrderLine, createPayment, fulfillOrder } from '../api'
import { cachePendingOrder } from './offline/db'
import { printReceipt } from './printReceipt'
import { formatMoney } from '../utils/formatters'

const METHODS = ['cash', 'card', 'esewa', 'khalti']

function vatFor(lines) {
  const taxable = lines.filter(l => l.tax_class === 'taxable').reduce((s, l) => s + l.line_total_paisa, 0)
  return Math.floor((taxable * 13) / 100)
}

// Renders as an inline panel state — no overlay, no fixed/backdrop.
export default function PaymentModal({ lines, session, locationId, outletName, onSuccess, onCancel }) {
  const subtotal   = lines.reduce((s, l) => s + l.line_total_paisa, 0)
  const vat        = vatFor(lines)
  const total      = subtotal + vat

  const [method, setMethod]         = useState('cash')
  const [ref, setRef]               = useState('')
  const [tendered, setTendered]     = useState('')
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')
  const [doneOrder, setDoneOrder]   = useState(null)

  const tenderedPaisa = method === 'cash' ? Math.round(parseFloat(tendered || 0) * 100) : total
  const changePaisa   = method === 'cash' && tenderedPaisa > 0 ? Math.max(0, tenderedPaisa - total) : 0

  // Progress survives a mid-submit failure so a retry resumes from the failed
  // step instead of creating a duplicate order/payment.
  const progress = useRef({ order: null, linesDone: false, paymentDone: false })

  async function submit() {
    if (method === 'cash' && tenderedPaisa < total) {
      setError('Cash tendered is less than total')
      return
    }
    setLoading(true)
    setError('')
    try {
      const order = {
        fulfilled_location: locationId,
        session: session?.id ?? null,
        source: 'counter',
        total_paisa: total,
      }

      if (!navigator.onLine && !progress.current.order) {
        await cachePendingOrder({ order, lines, payment: { method, ref, amount_paisa: total } })
        onSuccess({ offline: true })
        return
      }

      if (!progress.current.order) {
        const { data: createdOrder } = await createOrder(order)
        progress.current.order = createdOrder
      }
      const createdOrder = progress.current.order

      if (!progress.current.linesDone) {
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
        progress.current.linesDone = true
      }

      if (!progress.current.paymentDone) {
        await createPayment({
          order: createdOrder.id,
          method,
          amount_paisa: total,
          ref: ref || null,
        })
        progress.current.paymentDone = true
      }

      // Fulfilment transitions the order and writes the sale StockMovements.
      await fulfillOrder(createdOrder.id)
      setDoneOrder(createdOrder)
    } catch {
      setError(
        progress.current.order
          ? 'Could not finish the sale. Retry to resume — nothing will be charged twice.'
          : 'Payment failed. Check connection and try again.'
      )
    } finally {
      setLoading(false)
    }
  }

  function handlePrint() {
    printReceipt({ order: doneOrder, lines, method, tenderedPaisa, outletName, ref })
  }

  function handleDone() {
    onSuccess({ order: doneOrder })
  }

  if (doneOrder) {
    return (
      <div className="flex flex-col flex-1 overflow-y-auto bg-white p-6 text-center">
        <div className="w-14 h-14 bg-brand-success/10 rounded-full flex items-center justify-center mx-auto mb-3">
          <svg className="w-8 h-8 text-brand-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-lg font-bold mb-1">Payment Complete</h2>
        <p className="text-3xl font-bold text-brand-primary mb-1">{formatMoney(total)}</p>
        <p className="text-sm text-text-secondary mb-4">
          {method === 'cash' && changePaisa > 0
            ? `Change: ${formatMoney(changePaisa)}`
            : method.charAt(0).toUpperCase() + method.slice(1)}
        </p>
        <div className="flex gap-2 mt-auto">
          <button
            onClick={handlePrint}
            className="flex-1 border border-brand-border text-text-secondary py-2 rounded-lg text-sm hover:bg-brand-surface"
          >
            Print Receipt
          </button>
          <button
            onClick={handleDone}
            className="flex-1 bg-brand-primary hover:bg-brand-primaryHover text-white py-2 rounded-lg text-sm font-semibold"
          >
            Done
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-y-auto bg-white p-6">
      <h2 className="text-lg font-bold mb-1">Payment</h2>
      <p className="text-3xl font-bold text-brand-primary text-center mb-1">
        {formatMoney(total)}
      </p>
      {vat > 0 && (
        <p className="text-center text-xs text-amber-600 mb-4">
          incl. VAT {formatMoney(vat)}
        </p>
      )}
      {!vat && <div className="mb-4" />}

      {error && <p className="text-brand-danger text-sm mb-3">{error}</p>}
      {!navigator.onLine && (
        <p className="text-amber-600 text-xs mb-3 bg-amber-50 rounded px-3 py-2">
          Offline — order will be queued and synced when connection restores.
        </p>
      )}

      <div className="grid grid-cols-2 gap-2 mb-4">
        {METHODS.map((m) => (
          <button
            key={m}
            onClick={() => { setMethod(m); setRef(''); setTendered('') }}
            className={`py-2 rounded-lg text-sm font-medium border transition ${
              method === m
                ? 'bg-brand-primary text-white border-brand-primary'
                : 'border-brand-border text-text-secondary hover:border-brand-primary'
            }`}
          >
            {m.charAt(0).toUpperCase() + m.slice(1)}
          </button>
        ))}
      </div>

      {method === 'cash' && (
        <div className="mb-4">
          <label className="block text-xs text-text-secondary mb-1">Cash Tendered (Rs)</label>
          <input
            type="number"
            min={total / 100}
            step="1"
            placeholder={String(total / 100)}
            value={tendered}
            onChange={(e) => setTendered(e.target.value)}
            className="w-full border border-brand-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-primary"
          />
          {tenderedPaisa >= total && tenderedPaisa > 0 && (
            <p className="text-xs text-brand-primary mt-1 font-medium">
              Change: {formatMoney(changePaisa)}
            </p>
          )}
        </div>
      )}

      {method !== 'cash' && (
        <input
          type="text"
          placeholder="Reference / transaction ID"
          value={ref}
          onChange={(e) => setRef(e.target.value)}
          className="w-full border border-brand-border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:border-brand-primary"
        />
      )}

      <div className="flex gap-2 mt-auto">
        <button onClick={onCancel} className="flex-1 border border-brand-border text-text-secondary py-2 rounded-lg text-sm">
          Cancel
        </button>
        <button
          onClick={submit}
          disabled={loading}
          className="flex-1 bg-brand-primary hover:bg-brand-primaryHover text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
        >
          {loading ? 'Processing…' : 'Confirm Payment'}
        </button>
      </div>
    </div>
  )
}
