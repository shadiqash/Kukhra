import { useEffect, useRef, useState } from 'react'
import {
  checkoutOrder, createOrder, createOrderLine, createPayment, fulfillOrder,
  createPaymentIntent, verifyPaymentIntent,
} from '../api'
import { cachePendingOrder } from './offline/db'
import { printReceipt } from './printReceipt'
import { formatMoney, paisaToAmount, vatForLines } from '../utils/formatters'
import { uuid } from '../utils/uuid'

const METHODS = ['cash', 'card', 'fonepay']

// Settled by a gateway, so they cannot be taken offline and cannot be asserted
// by this screen — the server must hear it from the gateway itself.
const GATEWAY_METHODS = new Set(['fonepay', 'esewa', 'khalti'])

// Renders as an inline panel state — no overlay, no fixed/backdrop.
export default function PaymentModal({ lines, session, locationId, outletName, onSuccess, onCancel }) {
  // Prices are VAT-inclusive: the customer pays the subtotal, and VAT is the
  // portion already contained within it (shown for information, never added on
  // top). The order total the backend validates must equal the sum of line totals.
  const subtotal   = lines.reduce((s, l) => s + l.line_total_paisa, 0)
  const vat        = vatForLines(lines)
  const total      = subtotal

  const [method, setMethod]         = useState('cash')
  const [ref, setRef]               = useState('')
  const [tendered, setTendered]     = useState('')
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')
  const [doneOrder, setDoneOrder]   = useState(null)

  // The QR leg: an intent is money the customer has been asked for but has not
  // necessarily paid. It becomes spendable only when the server says the gateway
  // confirmed it.
  const [intent, setIntent]         = useState(null)
  const [polling, setPolling]       = useState(false)
  const [online, setOnline]         = useState(navigator.onLine)

  useEffect(() => {
    const sync = () => setOnline(navigator.onLine)
    window.addEventListener('online', sync)
    window.addEventListener('offline', sync)
    return () => {
      window.removeEventListener('online', sync)
      window.removeEventListener('offline', sync)
    }
  }, [])

  const isGateway = GATEWAY_METHODS.has(method)
  const verified = intent?.status === 'verified'

  const tenderedPaisa = method === 'cash' ? Math.round(parseFloat(tendered || 0) * 100) : total
  const changePaisa   = method === 'cash' && tenderedPaisa > 0 ? Math.max(0, tenderedPaisa - total) : 0

  // A gateway payment cannot be verified without a network, so it must not be
  // offered offline — queueing one would queue money nobody can prove was paid.
  const methodBlockedOffline = isGateway && !online

  async function startQr() {
    setLoading(true)
    setError('')
    try {
      const { data } = await createPaymentIntent({
        gateway: 'fonepay',
        amount_paisa: total,
        fulfilled_location: locationId,
        session: session?.id ?? null,
      })
      setIntent(data)
      setPolling(true)
    } catch (e) {
      setError(e?.response?.data?.detail ?? 'Could not reach the payment gateway. Take cash or card.')
    } finally {
      setLoading(false)
    }
  }

  // Poll until the gateway confirms. Terminal states stop the loop.
  useEffect(() => {
    if (!polling || !intent) return
    let cancelled = false

    const tick = setInterval(async () => {
      try {
        const { data } = await verifyPaymentIntent(intent.id)
        if (cancelled) return
        setIntent(data)
        if (data.status !== 'initiated') {
          setPolling(false)
          if (data.status === 'failed') {
            setError(data.failure_reason || 'Payment failed. Ask the customer to try again.')
          }
        }
      } catch {
        /* transient — keep polling; the cashier can always cancel */
      }
    }, 2500)

    return () => { cancelled = true; clearInterval(tick) }
  }, [polling, intent])

  function cancelQr() {
    setIntent(null)
    setPolling(false)
    setError('')
  }

  // Progress survives a mid-submit failure so a retry resumes from the failed
  // step instead of creating a duplicate order/payment.
  const progress = useRef({ order: null, linesDone: false, paymentDone: false, triedCheckout: false })

  // One idempotency key per cart (EF-01). Every attempt for this sale — the fast
  // atomic checkout, the step-by-step fallback, and any offline replay — carries
  // this same client_txn_id, so a checkout that committed but whose response was
  // lost is collapsed back to the original order server-side instead of ringing a
  // duplicate. Stable for the life of this modal instance (one cart).
  const txnId = useRef(uuid())

  async function submit() {
    if (method === 'cash' && tenderedPaisa < total) {
      setError('Cash tendered is less than total')
      return
    }
    if (isGateway && !verified) {
      setError('This payment has not been confirmed by the gateway yet.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const order = {
        client_txn_id: txnId.current,
        fulfilled_location: locationId,
        session: session?.id ?? null,
        source: 'counter',
        total_paisa: total,
      }
      const linePayloads = lines.map((l) => ({
        product: l.product_id,
        price: l.price_id,
        qty_kg: l.uom === 'kg' ? l.qty : 0,
        qty_pieces: l.uom === 'piece' ? l.qty : 0,
        line_total_paisa: l.line_total_paisa,
      }))
      const paymentPayload = {
        method,
        amount_paisa: total,
        ref: ref || null,
        ...(isGateway && { intent: intent.id }),
      }

      if (!navigator.onLine && !progress.current.order) {
        // Cash and card can be reconciled later from the paper trail. A gateway
        // payment cannot — there is no proof to queue — so it is never taken offline.
        if (isGateway) {
          setError('The network is down. Take cash or card instead.')
          return
        }
        await cachePendingOrder({ order, lines, payment: paymentPayload })
        onSuccess({ offline: true })
        return
      }

      // Fast path: one atomic request creates the order, its lines, its
      // payment, and fulfills it server-side in a single transaction — no
      // partial order possible. Only tried on the first attempt; once the
      // step-by-step fallback below has made progress, a retry must resume
      // that flow instead (re-running checkout here would double-create).
      if (!progress.current.order && !progress.current.triedCheckout) {
        progress.current.triedCheckout = true
        try {
          const { data: createdOrder } = await checkoutOrder({
            ...order,
            lines: linePayloads,
            payments: [paymentPayload],
          })
          setDoneOrder(createdOrder)
          return
        } catch (err) {
          if (err?.response?.status === 400) {
            // A definite rejection (e.g. insufficient stock) — surface it
            // directly; the step-by-step flow would only hit the same wall.
            setError(err.response.data?.detail ?? 'Payment failed. Check connection and try again.')
            return
          }
          // Network/server error — fall back to the resumable flow below.
        }
      }

      if (!progress.current.order) {
        const { data: createdOrder } = await createOrder(order)
        progress.current.order = createdOrder
      }
      const createdOrder = progress.current.order

      if (!progress.current.linesDone) {
        await Promise.all(
          linePayloads.map((l) => createOrderLine({ order: createdOrder.id, ...l }))
        )
        progress.current.linesDone = true
      }

      if (!progress.current.paymentDone) {
        await createPayment({ order: createdOrder.id, ...paymentPayload })
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
      {!online && (
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
            min={paisaToAmount(total)}
            step="1"
            placeholder={paisaToAmount(total)}
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

      {method === 'card' && (
        <input
          type="text"
          placeholder="Card slip number (optional)"
          value={ref}
          onChange={(e) => setRef(e.target.value)}
          className="w-full border border-brand-border rounded-lg px-3 py-2 text-sm mb-4 focus:outline-none focus:border-brand-primary"
        />
      )}

      {isGateway && (
        <div className="mb-4">
          {methodBlockedOffline ? (
            <p className="text-sm text-brand-danger bg-red-50 rounded-lg px-3 py-3">
              QR payment needs a connection — it cannot be confirmed offline.
              Take cash or card instead.
            </p>
          ) : !intent ? (
            <button
              onClick={startQr}
              disabled={loading}
              className="w-full border-[1.5px] border-brand-primary text-brand-primary py-3 rounded-lg text-sm font-semibold disabled:opacity-50"
            >
              {loading ? 'Generating QR…' : `Show QR for ${formatMoney(total)}`}
            </button>
          ) : (
            <div className="border-[1.5px] border-brand-border rounded-lg p-4 flex flex-col items-center gap-3">
              {/* The QR string comes from the gateway; it encodes the amount we asked for. */}
              <div className="font-mono text-[10px] break-all text-center text-text-secondary bg-brand-surface rounded p-3 w-full">
                {intent.qr_payload}
              </div>

              {verified ? (
                <p className="text-sm font-semibold text-brand-success">
                  ✓ Paid — {formatMoney(intent.amount_paisa)} confirmed by the gateway
                </p>
              ) : intent.status === 'failed' ? (
                <p className="text-sm font-semibold text-brand-danger">
                  Payment failed — nothing was taken
                </p>
              ) : (
                <p className="text-sm text-text-secondary flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  Waiting for the customer to pay…
                </p>
              )}

              <button
                onClick={cancelQr}
                className="text-xs text-text-secondary hover:text-brand-danger underline"
              >
                Cancel this QR
              </button>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2 mt-auto">
        <button onClick={onCancel} className="flex-1 border border-brand-border text-text-secondary py-2 rounded-lg text-sm">
          Cancel
        </button>
        <button
          onClick={submit}
          disabled={loading || (isGateway && !verified)}
          className="flex-1 bg-brand-primary hover:bg-brand-primaryHover text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Processing…' : isGateway && !verified ? 'Awaiting payment' : 'Confirm Payment'}
        </button>
      </div>
    </div>
  )
}
