import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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
  // Defaults to exact change as a real (not placeholder) value — most cash
  // sales are exact change, and a placeholder that mirrors the total looks
  // pre-filled but isn't, so Confirm Payment would otherwise fail on an
  // empty field for the most common case.
  const [tendered, setTendered]     = useState(paisaToAmount(total))
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
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className="flex flex-col flex-1 overflow-y-auto p-8 text-center bg-surface backdrop-blur-md"
      >
        <div className="w-16 h-16 bg-brand-success/10 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm animate-scale-in">
          <svg className="w-8 h-8 text-brand-success drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold mb-2 text-text-primary">Payment Complete</h2>
        <p className="text-4xl font-black text-brand-primary dark:text-brand-success mb-2 font-mono tracking-tight">
          {formatMoney(total)}
        </p>
        <p className="text-sm font-medium text-text-secondary bg-surface-active py-1.5 px-4 rounded-full inline-block mx-auto mb-6 shadow-sm border border-border">
          {method === 'cash' && changePaisa > 0
            ? `Change: ${formatMoney(changePaisa)}`
            : method.charAt(0).toUpperCase() + method.slice(1)}
        </p>
        <div className="flex gap-3 mt-auto">
          <button
            onClick={handlePrint}
            className="flex-1 bg-surface border border-border text-text-primary py-3.5 rounded-xl text-[15px] font-bold hover:bg-surface-hover hover:shadow-sm transition-all"
          >
            Print Receipt
          </button>
          <button
            onClick={handleDone}
            className="flex-1 bg-gradient-to-r from-brand-primary to-brand-primaryHover text-white py-3.5 rounded-xl text-[15px] font-bold shadow-md hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            Done
          </button>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className="flex flex-col flex-1 overflow-y-auto p-6 bg-surface backdrop-blur-sm custom-scrollbar"
    >
      <h2 className="text-lg font-bold mb-2 text-center text-text-secondary tracking-wide uppercase text-xs">Confirm Payment</h2>
      <p className="text-4xl font-black text-brand-primary dark:text-brand-success text-center mb-1 font-mono tracking-tight">
        {formatMoney(total)}
      </p>
      {vat > 0 && (
        <p className="text-center text-xs text-brand-secondary font-bold mb-6 bg-brand-secondary/10 py-1 px-3 rounded-full w-max mx-auto">
          incl. VAT {formatMoney(vat)}
        </p>
      )}
      {!vat && <div className="mb-6" />}

      {error && <p className="text-brand-danger bg-brand-danger/10 p-3 rounded-lg border border-brand-danger/20 text-sm font-medium mb-3">{error}</p>}
      {!online && (
        <p className="text-amber-600 dark:text-amber-400 text-xs font-semibold mb-3 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
          Offline — order will be queued and synced when connection restores.
        </p>
      )}

      <div className="grid grid-cols-3 gap-2 mb-6 bg-surface-hover p-1.5 rounded-xl border border-border">
        {METHODS.map((m) => (
          <button
            key={m}
            onClick={() => { setMethod(m); setRef(''); setTendered(m === 'cash' ? paisaToAmount(total) : '') }}
            className={`py-2.5 rounded-lg text-sm font-bold transition-all duration-200 ${
              method === m
                ? 'bg-surface text-brand-primary shadow-sm border border-border scale-[1.02]'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {m.charAt(0).toUpperCase() + m.slice(1)}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {method === 'cash' && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mb-4 overflow-hidden">
            <label className="block text-xs font-bold text-text-secondary mb-1.5">Cash Tendered (Rs)</label>
            <input
              type="number"
              min={paisaToAmount(total)}
              step="1"
              placeholder={paisaToAmount(total)}
              value={tendered}
              onChange={(e) => setTendered(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-[15px] font-semibold focus:outline-none focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 transition-all text-text-primary"
            />
            {tenderedPaisa >= total && tenderedPaisa > 0 && (
              <p className="text-[13px] text-brand-primary dark:text-brand-success mt-2 font-bold bg-brand-primary/10 dark:bg-brand-success/10 py-1.5 px-3 rounded-lg border border-brand-primary/20 inline-block">
                Change: {formatMoney(changePaisa)}
              </p>
            )}
          </motion.div>
        )}

        {method === 'card' && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mb-4 overflow-hidden">
            <input
              type="text"
              placeholder="Card slip number (optional)"
              value={ref}
              onChange={(e) => setRef(e.target.value)}
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-[15px] focus:outline-none focus:border-brand-primary focus:ring-4 focus:ring-brand-primary/10 transition-all text-text-primary placeholder:text-text-muted"
            />
          </motion.div>
        )}

        {isGateway && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="mb-4 overflow-hidden">
            {methodBlockedOffline ? (
              <p className="text-sm font-medium text-brand-danger bg-brand-danger/10 border border-brand-danger/20 rounded-xl px-4 py-3">
                QR payment needs a connection — it cannot be confirmed offline. Take cash or card instead.
              </p>
            ) : !intent ? (
              <button
                onClick={startQr}
                disabled={loading}
                className="w-full border-2 border-brand-primary text-brand-primary py-3.5 rounded-xl text-[15px] font-bold disabled:opacity-50 hover:bg-brand-primary/5 transition-colors"
              >
                {loading ? 'Generating QR…' : `Show QR for ${formatMoney(total)}`}
              </button>
            ) : (
              <div className="border-2 border-border rounded-xl p-5 flex flex-col items-center gap-4 bg-surface-active">
                {/* The QR string comes from the gateway; it encodes the amount we asked for. */}
                <div className="font-mono text-[11px] break-all text-center text-text-secondary bg-background border border-border rounded-lg p-3 w-full font-bold">
                  {intent.qr_payload}
                </div>

                {verified ? (
                  <p className="text-sm font-bold text-brand-success flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                    Paid — {formatMoney(intent.amount_paisa)} confirmed
                  </p>
                ) : intent.status === 'failed' ? (
                  <p className="text-sm font-bold text-brand-danger">
                    Payment failed — nothing was taken
                  </p>
                ) : (
                  <p className="text-[13px] font-semibold text-text-secondary flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
                    Waiting for the customer to pay…
                  </p>
                )}

                <button
                  onClick={cancelQr}
                  className="text-[13px] font-semibold text-text-muted hover:text-brand-danger transition-colors underline underline-offset-2"
                >
                  Cancel this QR
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex gap-3 mt-auto pt-6 border-t border-border shrink-0">
        <button onClick={onCancel} className="flex-1 bg-surface border border-border text-text-primary py-3.5 rounded-xl text-[15px] font-bold hover:bg-surface-hover transition-all hover:shadow-sm">
          Cancel
        </button>
        <button
          onClick={submit}
          disabled={loading || (isGateway && !verified)}
          className="flex-1 bg-gradient-to-r from-brand-primary to-brand-primaryHover text-white py-3.5 rounded-xl text-[15px] font-bold shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] transition-all"
        >
          {loading ? 'Processing…' : isGateway && !verified ? 'Awaiting payment' : 'Confirm Payment'}
        </button>
      </div>
    </motion.div>
  )
}
