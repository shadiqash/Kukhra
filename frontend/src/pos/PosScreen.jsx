import { useCallback, useEffect, useRef, useState } from 'react'
import { ShoppingCart } from 'lucide-react'
import { getProducts, getPrices, getCounters, getSessions } from '../api'
import { cacheProducts, getCachedProducts, getPendingOrders, deletePendingOrder, cachePendingOrder, updatePendingOrder, getHeldOrders, putHeldOrder, deleteHeldOrder } from './offline/db'
import { checkoutOrder, createOrder, createOrderLine, createPayment, fulfillOrder } from '../api'
import { useAuth } from '../auth/AuthContext'
import { useConfirm } from '../ui/ConfirmDialog'
import { useToast } from '../ui/Toast'
import { usePageTitle } from '../hooks/usePageTitle'
import { useTheme } from '../hooks/useTheme'
import { formatMoney } from '../utils/formatters'
import { uuid } from '../utils/uuid'
import Cart from './Cart'
import PaymentModal from './PaymentModal'
import ShiftModal from './ShiftModal'
import { motion, AnimatePresence } from 'framer-motion'
import { Sun, Moon } from 'lucide-react'

// Prices are VAT-inclusive, so the grand total is just the sum of the line
// totals — VAT is already contained within each one and is broken out for the
// receipt/invoice only (see utils/formatters vatForLines).
function grandTotal(lines) {
  return lines.reduce((s, l) => s + l.line_total_paisa, 0)
}

export default function PosScreen() {
  const { user, logout } = useAuth()
  const confirm = useConfirm()
  const { isDark, toggleTheme } = useTheme()
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
  const cartPanel = (
    <AnimatePresence mode="wait">
      {showPayment ? (
        <PaymentModal
          key="payment"
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
        <motion.div
          key="cart"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className="flex-1 flex flex-col h-full w-full absolute inset-0 bg-surface rounded-[inherit]"
        >
          <div className="p-4 border-b border-border flex items-center justify-between shrink-0">
            <h2 className="font-semibold text-text-primary">Cart</h2>
            {lines.length > 0 && (
              <div className="flex gap-2">
                <button
                  onClick={holdOrder}
                  className="text-xs border border-amber-500/50 text-amber-600 dark:text-amber-400 px-3 py-1.5 rounded-lg hover:bg-amber-500/10 transition-colors font-medium"
                >
                  Hold
                </button>
                <button
                  onClick={voidOrder}
                  className="text-xs border border-brand-danger/50 text-brand-danger px-3 py-1.5 rounded-lg hover:bg-brand-danger/10 transition-colors font-medium"
                >
                  Void
                </button>
              </div>
            )}
          </div>
          <div className="flex-1 flex flex-col overflow-hidden p-2 min-h-0">
            <Cart lines={lines} onRemove={removeFromCart} onQtyChange={updateQty} />
          </div>
          <div className="p-4 border-t border-border space-y-2 shrink-0 bg-surface-hover">
            <button
              onClick={() => setShowPayment(true)}
              disabled={lines.length === 0 || !hasSession}
              className="w-full bg-gradient-to-r from-brand-primary to-brand-primaryHover text-white font-bold py-3.5 rounded-xl shadow-md hover:shadow-lg disabled:opacity-40 disabled:hover:scale-100 disabled:hover:shadow-md hover:scale-[1.02] active:scale-[0.98] text-sm transition-all"
            >
              Pay — {formatMoney(total)}
            </button>
            {!hasSession && (
              <p className="text-center text-xs text-amber-600 dark:text-amber-400 font-medium pt-1">Open a shift to accept payments</p>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )

  return (
    <div className="h-screen flex flex-col bg-background font-sans transition-colors duration-300">
      {/* Header */}
      <header className="glass-dark px-6 py-4 flex items-center gap-4 z-20 border-b border-white/10 shadow-md">
        <span className="font-black text-xl flex-1 tracking-tight text-text-inverse drop-shadow-md">Everfresh POS</span>
        {!online && (
          <span className="text-xs bg-amber-500 px-3 py-1 rounded-full font-bold text-white shadow-sm">OFFLINE</span>
        )}
        {heldOrders.length > 0 && (
          <button
            onClick={() => setShowHeld(true)}
            className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-3 py-1 rounded-full font-bold transition-colors shadow-sm"
          >
            {heldOrders.length} Held
          </button>
        )}
        <span className="text-sm font-medium text-text-inverse/80">{user?.username}</span>
        <button onClick={toggleTheme} className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-white/90 hover:bg-white/20 transition-colors shadow-sm" title="Toggle Theme">
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button
          onClick={() => setShowShift(true)}
          disabled={!hasSession && !counterLoaded}
          className={`text-xs px-4 py-1.5 rounded-full font-bold border transition-colors shadow-sm disabled:opacity-40 disabled:cursor-not-allowed ${
            hasSession
              ? 'border-brand-danger/40 bg-brand-danger hover:bg-red-800 text-white'
              : 'border-white/40 hover:bg-white/10 text-white'
          }`}
        >
          {hasSession ? 'Close Shift' : counterLoaded ? 'Open Shift' : 'Loading…'}
        </button>
        <button onClick={logout} className="text-xs font-semibold text-text-inverse/70 hover:text-text-inverse transition-colors ml-2">
          Sign out
        </button>
      </header>

      <div className="flex flex-1 min-h-0">
        {/* Product grid */}
        <div className="flex-1 flex flex-col p-4 md:p-6 min-w-0">
          <input
            type="text"
            placeholder="Search products or scan barcode…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full border-2 border-border rounded-xl px-5 py-3.5 text-[15px] font-medium mb-6 focus:outline-none focus:border-brand-primary bg-surface text-text-primary placeholder:text-text-muted shadow-sm transition-all"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 overflow-y-auto px-1 pb-6 custom-scrollbar">
            {filtered.map((p) => {
              const price = prices[p.id]
              return (
                <button
                  key={p.id}
                  onClick={() => addToCart(p)}
                  disabled={!hasSession}
                  className="glass rounded-2xl p-5 text-left hover:scale-[1.04] hover:shadow-xl hover:border-brand-primary/30 dark:hover:border-brand-primary/50 active:scale-[0.97] transition-all duration-200 ease-out disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 flex flex-col relative min-h-[164px] group"
                >
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-brand-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                  <p className="font-bold text-[15px] text-text-primary mb-1 relative z-10 leading-tight">{p.name}</p>
                  <p className="text-xs font-medium text-text-secondary">
                    {p.uom}
                    {p.tax_class === 'taxable' && <span className="ml-1.5 text-amber-600 dark:text-amber-400 font-bold">incl. VAT</span>}
                  </p>
                  <div className="mt-auto pt-3">
                    {price ? (
                      <p className="text-brand-primary dark:text-brand-success font-black text-[15px] font-mono tracking-tight">
                        {formatMoney(price.price_paisa)}
                      </p>
                    ) : (
                      <p className="text-text-muted text-xs font-semibold">No price</p>
                    )}
                  </div>
                </button>
              )
            })}
            {filtered.length === 0 && (
              <p className="col-span-full text-center text-text-muted text-sm mt-10 font-medium">No products found</p>
            )}
          </div>
        </div>

        {/* Cart panel — payment and receipt render inline here, not as overlays.
            Hidden below md, where the floating button + bottom sheet take over. */}
        <div className="w-[360px] bg-surface border border-border hidden md:flex flex-col overflow-hidden my-6 mr-6 rounded-3xl shadow-xl relative z-10 animate-fade-in">
          {isDesktop && cartPanel}
        </div>
      </div>

      {/* Mobile cart — floating button opens the cart as a bottom sheet */}
      {!isDesktop && !showCartMobile && (
        <button
          onClick={() => setShowCartMobile(true)}
          className="md:hidden fixed bottom-6 right-6 z-40 h-[60px] pl-5 pr-6 bg-brand-primary text-white rounded-full shadow-xl flex items-center gap-3 font-bold text-[15px] hover:scale-105 active:scale-95 transition-all"
          aria-label="Open cart"
        >
          <span className="relative">
            <ShoppingCart size={24} />
            {lines.length > 0 && (
              <span className="absolute -top-2.5 -right-2.5 bg-amber-500 text-[11px] font-black rounded-full min-w-[20px] h-[20px] flex items-center justify-center px-1 border-2 border-brand-primary">
                {lines.length}
              </span>
            )}
          </span>
          <span className="font-mono tracking-tight">{formatMoney(total)}</span>
        </button>
      )}
      {!isDesktop && showCartMobile && (
        <div className="md:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowCartMobile(false)} />
          <motion.div 
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="absolute inset-x-0 bottom-0 h-[85vh] bg-surface rounded-t-[32px] flex flex-col overflow-hidden shadow-2xl"
          >
            <button
              onClick={() => setShowCartMobile(false)}
              className="w-full flex justify-center py-4 border-b border-border shrink-0"
              aria-label="Close cart"
            >
              <span className="w-12 h-1.5 bg-border rounded-full" />
            </button>
            <div className="flex-1 relative">
              {cartPanel}
            </div>
          </motion.div>
        </div>
      )}

      {/* Held orders panel */}
      {showHeld && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface rounded-3xl shadow-2xl w-full max-w-sm p-7 border border-border"
          >
            <h2 className="text-xl font-bold text-text-primary mb-5 tracking-tight">Held Orders</h2>
            <div className="space-y-3 max-h-60 overflow-y-auto custom-scrollbar pr-2">
              {heldOrders.map((held, idx) => (
                <button
                  key={idx}
                  onClick={() => resumeHeld(idx)}
                  className="w-full flex items-center justify-between text-left border-2 border-border rounded-xl px-4 py-3 hover:border-brand-primary bg-surface transition-all"
                >
                  <div>
                    <span className="font-bold text-text-primary block">{held.lines.length} item(s)</span>
                    <span className="text-xs text-text-muted font-medium mt-0.5 block">
                      {new Date(held.heldAt).toLocaleTimeString()}
                    </span>
                  </div>
                  <span className="text-brand-primary dark:text-brand-success font-black font-mono text-[15px]">
                    {formatMoney(grandTotal(held.lines))}
                  </span>
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowHeld(false)}
              className="mt-6 w-full border-2 border-border text-text-secondary font-bold py-3 rounded-xl text-[15px] hover:bg-surface-hover transition-colors"
            >
              Cancel
            </button>
          </motion.div>
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
