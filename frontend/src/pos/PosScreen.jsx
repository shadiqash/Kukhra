import { useCallback, useEffect, useRef, useState } from 'react'
import { ShoppingCart } from 'lucide-react'
import { getProducts, getPrices, getCounters, getSessions } from '../api'
import { cacheProducts, getCachedProducts, getPendingOrders, deletePendingOrder, cachePendingOrder, updatePendingOrder, getHeldOrders, putHeldOrder, deleteHeldOrder } from './offline/db'
import { checkoutOrder, createOrder, createOrderLine, createPayment, fulfillOrder } from '../api'
import { useAuth } from '../auth/AuthContext'
import { useConfirm } from '../ui/ConfirmDialog'
import { useToast } from '../ui/Toast'
import { usePageTitle } from '../hooks/usePageTitle'
import { formatMoney } from '../utils/formatters'
import { uuid } from '../utils/uuid'
import Cart from './Cart'
import PaymentModal from './PaymentModal'
import ShiftModal from './ShiftModal'

// Prices are VAT-inclusive, so the grand total is just the sum of the line
// totals — VAT is already contained within each one and is broken out for the
// receipt/invoice only (see utils/formatters vatForLines).
function grandTotal(lines) {
  return lines.reduce((s, l) => s + l.line_total_paisa, 0)
}

export default function PosScreen() {
  const { user, logout } = useAuth()
  const confirm = useConfirm()
  usePageTitle('Point of Sale')
  const [products, setProducts] = useState([])
  const [prices, setPrices] = useState({})
  const [search, setSearch] = useState('')
  const [lines, setLines] = useState([])
  const [heldOrders, setHeldOrders] = useState([])
  const [showHeld, setShowHeld] = useState(false)
  const [session, setSession] = useState(null)
  const [counter, setCounter] = useState(null)
  const [showShift, setShowShift] = useState(false)
  const [showPayment, setShowPayment] = useState(false)
  // Below md the cart side panel is hidden; a floating button opens it as a
  // bottom sheet instead of forcing the cashier to scroll past the whole grid.
  // Tracked in JS (not just CSS) so the panel — and the PaymentModal inside it,
  // which holds an idempotency key — is only ever mounted in one place.
  const [showCartMobile, setShowCartMobile] = useState(false)
  const [isDesktop, setIsDesktop] = useState(() => window.matchMedia('(min-width: 768px)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 768px)')
    const sync = (e) => setIsDesktop(e.matches)
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])
  // Reactive connectivity (EF-07): reading navigator.onLine inline in JSX never
  // re-renders on a change. Track it in state driven by the online/offline events.
  const [online, setOnline] = useState(navigator.onLine)
  const toast = useToast()

  useEffect(() => {
    const sync = () => setOnline(navigator.onLine)
    window.addEventListener('online', sync)
    window.addEventListener('offline', sync)
    return () => {
      window.removeEventListener('online', sync)
      window.removeEventListener('offline', sync)
    }
  }, [])

  // Rehydrate parked carts from IndexedDB on mount so a refresh/crash doesn't lose
  // them (EF-05).
  useEffect(() => {
    getHeldOrders().then((held) => {
      if (held.length) setHeldOrders(held.sort((a, b) => a.heldAt - b.heldAt))
    }).catch(() => {})
  }, [])

  const showToast = (msg) => toast.success(msg)

  // Load products (with offline fallback)
  useEffect(() => {
    async function load() {
      try {
        const [prodRes, priceRes] = await Promise.all([
          getProducts(),
          getPrices({ active: true, tier: 'retail' }),
        ])
        await cacheProducts(prodRes.data.results ?? prodRes.data)
        setProducts(prodRes.data.results ?? prodRes.data)
        const map = {}
        ;(priceRes.data.results ?? priceRes.data).forEach((p) => {
          map[p.product] = p
        })
        setPrices(map)
      } catch {
        const cached = await getCachedProducts()
        setProducts(cached)
      }
    }
    load()
  }, [])

  // Load the counter for this cashier and resume any shift still open on the
  // server (reload/crash mid-shift — without this the till locks up with
  // "counter already has an open session"). The server scopes the counter list
  // to the cashier's assigned outlets, so an empty list means the account
  // isn't assigned anywhere.
  const [counterLoaded, setCounterLoaded] = useState(false)
  useEffect(() => {
    async function bind() {
      try {
        const [counterRes, sessionRes] = await Promise.all([getCounters(), getSessions()])
        const counters = counterRes.data.results ?? counterRes.data
        const sessions = sessionRes.data.results ?? sessionRes.data
        const open = sessions.find((s) => !s.closed_at)
        if (open) {
          setSession(open)
          // Bind the till to the counter the open shift is running on, so a
          // resumed shift keeps selling against the same outlet.
          setCounter(counters.find((c) => c.id === open.counter) ?? counters[0] ?? null)
        } else if (counters.length > 0) {
          setCounter(counters[0])
        }
        setCounterLoaded(true)
      } catch {
        // Offline or server unreachable — the cached-products path still works.
      }
    }
    bind()
  }, [])

  // Sync pending offline orders when back online
  const syncingRef = useRef(false)
  useEffect(() => {
    async function replayPending() {
        const pending = await getPendingOrders()
        for (const p of pending) {
          const linePayloads = p.lines.map((l) => ({
            product: l.product_id,
            price: l.price_id,
            qty_kg: l.uom === 'kg' ? l.qty : 0,
            qty_pieces: l.uom === 'piece' ? l.qty : 0,
            line_total_paisa: l.line_total_paisa,
          }))

          // Once a prior attempt has already created the order server-side,
          // the atomic checkout can no longer be used (it would create a
          // second order) — resume the step-by-step replay from whatever it
          // last completed, tracked on the queued record itself so this
          // survives across separate sync runs/page reloads.
          if (!p.createdOrder) {
            try {
              // Fast path: one atomic request replays the whole sale server-side.
              await checkoutOrder({ ...p.order, lines: linePayloads, payments: [p.payment] })
              await deletePendingOrder(p.localId)
              continue
            } catch (err) {
              // A definite rejection (e.g. insufficient stock) rolled back
              // cleanly server-side — leave it queued rather than falling
              // through to the step-by-step replay, which would otherwise
              // create a stuck, never-fulfillable duplicate order on every
              // future sync attempt.
              if (err?.response?.status === 400) continue
              /* transient/network failure — fall back to the step-by-step replay below */
            }
          }

          try {
            let createdOrder = p.createdOrder
            if (!createdOrder) {
              ;({ data: createdOrder } = await createOrder(p.order))
              await updatePendingOrder(p.localId, { createdOrder })
            }
            if (!p.linesDone) {
              await Promise.all(linePayloads.map((l) => createOrderLine({ order: createdOrder.id, ...l })))
              await updatePendingOrder(p.localId, { linesDone: true })
            }
            if (!p.paymentDone) {
              await createPayment({ order: createdOrder.id, ...p.payment })
              await updatePendingOrder(p.localId, { paymentDone: true })
            }
            await fulfillOrder(createdOrder.id)
            await deletePendingOrder(p.localId)
          } catch {
            /* leave in queue, resuming from whichever step last completed */
          }
        }
    }

    async function syncPending() {
      if (!navigator.onLine || syncingRef.current) return
      syncingRef.current = true
      try {
        // Serialize replay across tabs (EF-08): with two POS tabs both regaining
        // connectivity, an exclusive Web Lock lets exactly one drain the shared
        // pending_orders queue; ifAvailable yields null in the others and they skip.
        // (EF-01's idempotency key already makes a double-replay harmless — this
        // just avoids the wasted duplicate request.)
        if (navigator.locks?.request) {
          await navigator.locks.request('everfresh-pos-sync', { ifAvailable: true }, async (lock) => {
            if (lock) await replayPending()
          })
        } else {
          await replayPending()
        }
      } finally {
        syncingRef.current = false
      }
    }
    window.addEventListener('online', syncPending)
    syncPending()
    return () => window.removeEventListener('online', syncPending)
  }, [])

  const addToCart = useCallback(
    (product) => {
      const price = prices[product.id]
      if (!price) { showToast('No active price for this product'); return }
      setLines((prev) => {
        const existing = prev.findIndex((l) => l.product_id === product.id)
        if (existing >= 0) {
          return prev.map((l, i) =>
            i === existing
              ? { ...l, qty: l.qty + 1, line_total_paisa: (l.qty + 1) * l.price_paisa }
              : l
          )
        }
        return [
          ...prev,
          {
            product_id: product.id,
            product_name: product.name,
            tax_class: product.tax_class,
            price_id: price.id,
            price_paisa: price.price_paisa,
            uom: product.uom,
            qty: 1,
            line_total_paisa: price.price_paisa,
          },
        ]
      })
    },
    [prices]
  )

  const removeFromCart = (idx) => setLines((prev) => prev.filter((_, i) => i !== idx))

  const updateQty = (idx, qty) => {
    if (qty <= 0) { removeFromCart(idx); return }
    setLines((prev) =>
      prev.map((l, i) =>
        i === idx ? { ...l, qty, line_total_paisa: Math.round(qty * l.price_paisa) } : l
      )
    )
  }

  const holdOrder = () => {
    if (lines.length === 0) return
    const held = { id: uuid(), lines, heldAt: Date.now() }
    setHeldOrders((prev) => [...prev, held])
    setLines([])
    // Persist so the parked cart survives a reload/crash (EF-05); state is only a mirror.
    putHeldOrder(held).catch(() => {})
    showToast('Order held')
  }

  const voidOrder = async () => {
    if (lines.length === 0) return
    const ok = await confirm({
      title: 'Void this order?',
      message: 'All items will be removed from the cart.',
      confirmLabel: 'Void order',
      danger: true,
    })
    if (ok) {
      setLines([])
      showToast('Order voided')
    }
  }

  const resumeHeld = async (idx) => {
    const held = heldOrders[idx]
    if (lines.length > 0) {
      const ok = await confirm({
        title: 'Replace current cart?',
        message: 'The items currently in the cart will be replaced by the held order.',
        confirmLabel: 'Replace',
      })
      if (!ok) return
    }
    setLines(held.lines)
    setHeldOrders((prev) => prev.filter((_, i) => i !== idx))
    if (held.id) deleteHeldOrder(held.id).catch(() => {})
    setShowHeld(false)
    showToast('Order resumed')
  }

  const filtered = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.barcode && p.barcode.includes(search))
  )

  const hasSession = !!session
  const total = grandTotal(lines)

  // Shared between the desktop side panel and the mobile bottom sheet.
  const cartPanel = showPayment ? (
    <PaymentModal
      lines={lines}
      session={session}
      locationId={counter?.location}
      outletName={counter?.name}
      onSuccess={({ offline }) => {
        setLines([])
        setShowPayment(false)
        setShowCartMobile(false)
        if (offline) showToast('Order queued (offline)')
      }}
      onCancel={() => setShowPayment(false)}
    />
  ) : (
    <>
      <div className="p-4 border-b border-brand-border flex items-center justify-between">
        <h2 className="font-semibold text-text-primary">Cart</h2>
        {lines.length > 0 && (
          <div className="flex gap-2">
            <button
              onClick={holdOrder}
              className="text-xs border border-amber-300 text-amber-700 px-2 py-1 rounded hover:bg-amber-50 transition-colors"
            >
              Hold
            </button>
            <button
              onClick={voidOrder}
              className="text-xs border border-brand-danger/30 text-brand-danger px-2 py-1 rounded hover:bg-[#fef2f2] transition-colors"
            >
              Void
            </button>
          </div>
        )}
      </div>
      <div className="flex-1 flex flex-col overflow-hidden p-2">
        <Cart lines={lines} onRemove={removeFromCart} onQtyChange={updateQty} />
      </div>
      <div className="p-4 border-t border-brand-border space-y-2">
        <button
          onClick={() => setShowPayment(true)}
          disabled={lines.length === 0 || !hasSession}
          className="w-full bg-brand-primary hover:bg-brand-primaryHover text-white font-semibold py-2.5 rounded-lg disabled:opacity-40 text-sm transition-colors"
        >
          Pay — {formatMoney(total)}
        </button>
        {!hasSession && (
          <p className="text-center text-xs text-amber-600">Open a shift to accept payments</p>
        )}
      </div>
    </>
  )

  return (
    <div className="h-screen flex flex-col bg-brand-surface font-sans">
      {/* Header */}
      <header className="bg-brand-primary text-white px-4 py-3 flex items-center gap-3">
        <span className="font-bold text-lg flex-1 tracking-wide">Everfresh POS</span>
        {!online && (
          <span className="text-xs bg-amber-500 px-2 py-0.5 rounded-full font-semibold">OFFLINE</span>
        )}
        {heldOrders.length > 0 && (
          <button
            onClick={() => setShowHeld(true)}
            className="text-xs bg-amber-500 hover:bg-amber-600 px-3 py-1 rounded-full font-semibold transition-colors"
          >
            {heldOrders.length} Held
          </button>
        )}
        <span className="text-sm text-white/80">{user?.username}</span>
        <button
          onClick={() => setShowShift(true)}
          className={`text-xs px-3 py-1 rounded-full font-semibold border transition-colors ${
            hasSession
              ? 'border-brand-danger/40 bg-brand-danger hover:bg-[#991b1b]'
              : 'border-white/60 hover:bg-white/10'
          }`}
        >
          {hasSession ? 'Close Shift' : 'Open Shift'}
        </button>
        <button onClick={logout} className="text-xs text-white/70 hover:text-white transition-colors">
          Sign out
        </button>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Product grid */}
        <div className="flex-1 flex flex-col p-4 min-w-0">
          <input
            type="text"
            placeholder="Search products or scan barcode…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full border-[1.5px] border-brand-border rounded-xl px-4 py-2.5 text-sm mb-4 focus:outline-none focus:border-brand-primary bg-white"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 overflow-y-auto">
            {filtered.map((p) => {
              const price = prices[p.id]
              return (
                <button
                  key={p.id}
                  onClick={() => addToCart(p)}
                  disabled={!hasSession}
                  className="bg-white rounded-xl shadow-sm border-[1.5px] border-brand-border p-3 text-left hover:border-brand-primary hover:shadow-md transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <p className="font-medium text-sm text-text-primary mb-1">{p.name}</p>
                  <p className="text-xs text-text-secondary">
                    {p.uom}
                    {p.tax_class === 'taxable' && <span className="ml-1 text-amber-600">incl. VAT</span>}
                  </p>
                  {price ? (
                    <p className="text-brand-primary font-bold text-sm mt-1 font-mono">
                      {formatMoney(price.price_paisa)}
                    </p>
                  ) : (
                    <p className="text-text-secondary/60 text-xs mt-1">No price</p>
                  )}
                </button>
              )
            })}
            {filtered.length === 0 && (
              <p className="col-span-full text-center text-text-secondary text-sm mt-8">No products found</p>
            )}
          </div>
        </div>

        {/* Cart panel — payment and receipt render inline here, not as overlays.
            Hidden below md, where the floating button + bottom sheet take over. */}
        <div className="w-72 bg-white border-l-[1.5px] border-brand-border hidden md:flex flex-col overflow-hidden">
          {isDesktop && cartPanel}
        </div>
      </div>

      {/* Mobile cart — floating button opens the cart as a bottom sheet */}
      {!isDesktop && !showCartMobile && (
        <button
          onClick={() => setShowCartMobile(true)}
          className="md:hidden fixed bottom-4 right-4 z-40 h-14 pl-4 pr-5 bg-brand-primary text-white rounded-full shadow-xl flex items-center gap-2.5 font-semibold text-sm"
          aria-label="Open cart"
        >
          <span className="relative">
            <ShoppingCart size={22} />
            {lines.length > 0 && (
              <span className="absolute -top-2 -right-2 bg-amber-500 text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                {lines.length}
              </span>
            )}
          </span>
          <span className="font-mono">{formatMoney(total)}</span>
        </button>
      )}
      {!isDesktop && showCartMobile && (
        <div className="md:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/45" onClick={() => setShowCartMobile(false)} />
          <div className="absolute inset-x-0 bottom-0 top-20 bg-white rounded-t-2xl flex flex-col overflow-hidden shadow-2xl">
            <button
              onClick={() => setShowCartMobile(false)}
              className="w-full flex justify-center py-2.5 border-b border-brand-border shrink-0"
              aria-label="Close cart"
            >
              <span className="w-10 h-1 bg-gray-300 rounded-full" />
            </button>
            {cartPanel}
          </div>
        </div>
      )}

      {/* Held orders panel */}
      {showHeld && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
            <h2 className="text-lg font-bold text-text-primary mb-4">Held Orders</h2>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {heldOrders.map((held, idx) => (
                <button
                  key={idx}
                  onClick={() => resumeHeld(idx)}
                  className="w-full text-left border-[1.5px] border-brand-border rounded-lg px-3 py-2 hover:border-brand-primary text-sm transition-colors"
                >
                  <span className="font-medium text-text-primary">{held.lines.length} item(s)</span>
                  <span className="text-text-secondary ml-2 font-mono">
                    {formatMoney(grandTotal(held.lines))}
                  </span>
                  <span className="text-xs text-text-secondary/70 ml-2">
                    {new Date(held.heldAt).toLocaleTimeString()}
                  </span>
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowHeld(false)}
              className="mt-4 w-full border-[1.5px] border-brand-border text-text-secondary py-2 rounded-lg text-sm hover:bg-brand-surface transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      {showShift && (
        <ShiftModal
          session={hasSession ? session : null}
          counterId={counter?.id}
          onOpen={(s) => { setSession(s); setShowShift(false); showToast('Shift opened') }}
          onClose={() => { setSession(null); setShowShift(false) }}
          onDismiss={() => setShowShift(false)}
        />
      )}
    </div>
  )
}
