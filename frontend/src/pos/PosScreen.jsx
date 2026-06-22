import { useCallback, useEffect, useState } from 'react'
import { getProducts, getPrices, getCounters } from '../api'
import { cacheProducts, getCachedProducts, getPendingOrders, deletePendingOrder, cachePendingOrder } from './offline/db'
import { createOrder, createOrderLine, createPayment } from '../api'
import { useAuth } from '../auth/AuthContext'
import Cart from './Cart'
import PaymentModal from './PaymentModal'
import ShiftModal from './ShiftModal'

export default function PosScreen() {
  const { user, logout } = useAuth()
  const [products, setProducts] = useState([])
  const [prices, setPrices] = useState({})
  const [search, setSearch] = useState('')
  const [lines, setLines] = useState([])
  const [session, setSession] = useState(null)
  const [counter, setCounter] = useState(null)
  const [showShift, setShowShift] = useState(false)
  const [showPayment, setShowPayment] = useState(false)
  const [toast, setToast] = useState('')

  const showToast = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  // Load products (with offline fallback)
  useEffect(() => {
    async function load() {
      try {
        const [prodRes, priceRes] = await Promise.all([
          getProducts({ is_active: true }),
          getPrices({ valid_to__isnull: true, tier: 'retail' }),
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

  // Load counter for this cashier
  useEffect(() => {
    getCounters()
      .then(({ data }) => {
        const list = data.results ?? data
        if (list.length > 0) setCounter(list[0])
      })
      .catch(() => {})
  }, [])

  // Sync pending offline orders when back online
  useEffect(() => {
    async function syncPending() {
      if (!navigator.onLine) return
      const pending = await getPendingOrders()
      for (const p of pending) {
        try {
          const { data: createdOrder } = await createOrder(p.order)
          await Promise.all(
            p.lines.map((l) =>
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
          await createPayment({ order: createdOrder.id, ...p.payment })
          await deletePendingOrder(p.localId)
        } catch {
          /* leave in queue */
        }
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

  const filtered = products.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.barcode && p.barcode.includes(search))
  )

  const hasSession = !!session
  const total = lines.reduce((s, l) => s + l.line_total_paisa, 0)

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-green-700 text-white px-4 py-3 flex items-center gap-3">
        <span className="font-bold text-lg flex-1">Everfresh POS</span>
        {!navigator.onLine && (
          <span className="text-xs bg-amber-500 px-2 py-0.5 rounded-full">OFFLINE</span>
        )}
        <span className="text-sm opacity-80">{user?.username}</span>
        <button
          onClick={() => setShowShift(true)}
          className={`text-xs px-3 py-1 rounded-full font-medium border ${
            hasSession
              ? 'border-red-300 bg-red-600 hover:bg-red-700'
              : 'border-white hover:bg-green-600'
          }`}
        >
          {hasSession ? 'Close Shift' : 'Open Shift'}
        </button>
        <button onClick={logout} className="text-xs opacity-70 hover:opacity-100">
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
            className="w-full border border-gray-200 rounded-xl px-4 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 overflow-y-auto">
            {filtered.map((p) => {
              const price = prices[p.id]
              return (
                <button
                  key={p.id}
                  onClick={() => addToCart(p)}
                  disabled={!hasSession}
                  className="bg-white rounded-xl shadow-sm border border-gray-100 p-3 text-left hover:border-green-400 hover:shadow-md transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <p className="font-medium text-sm text-gray-800 mb-1">{p.name}</p>
                  <p className="text-xs text-gray-500">{p.uom}</p>
                  {price ? (
                    <p className="text-green-700 font-bold text-sm mt-1">
                      Rs {(price.price_paisa / 100).toFixed(2)}
                    </p>
                  ) : (
                    <p className="text-gray-400 text-xs mt-1">No price</p>
                  )}
                </button>
              )
            })}
            {filtered.length === 0 && (
              <p className="col-span-full text-center text-gray-400 text-sm mt-8">No products found</p>
            )}
          </div>
        </div>

        {/* Cart panel */}
        <div className="w-72 bg-white border-l border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Cart</h2>
          </div>
          <div className="flex-1 flex flex-col overflow-hidden p-2">
            <Cart lines={lines} onRemove={removeFromCart} onQtyChange={updateQty} />
          </div>
          <div className="p-4 border-t border-gray-100 space-y-2">
            <button
              onClick={() => setLines([])}
              disabled={lines.length === 0}
              className="w-full border border-gray-200 text-gray-600 text-sm py-2 rounded-lg disabled:opacity-40"
            >
              Clear
            </button>
            <button
              onClick={() => setShowPayment(true)}
              disabled={lines.length === 0 || !hasSession}
              className="w-full bg-green-600 text-white font-semibold py-2 rounded-lg disabled:opacity-40 text-sm"
            >
              Pay — Rs {(total / 100).toFixed(2)}
            </button>
            {!hasSession && (
              <p className="text-center text-xs text-amber-600">Open a shift to accept payments</p>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      {showShift && (
        <ShiftModal
          session={hasSession ? session : null}
          counterId={counter?.id}
          onOpen={(s) => { setSession(s); setShowShift(false); showToast('Shift opened') }}
          onClose={() => { setSession(null); setShowShift(false); showToast('Shift closed') }}
          onDismiss={() => setShowShift(false)}
        />
      )}
      {showPayment && (
        <PaymentModal
          lines={lines}
          session={session}
          locationId={counter?.location}
          onSuccess={({ offline }) => {
            setLines([])
            setShowPayment(false)
            showToast(offline ? 'Order queued (offline)' : 'Payment complete')
          }}
          onCancel={() => setShowPayment(false)}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-sm px-4 py-2 rounded-full shadow-lg z-50">
          {toast}
        </div>
      )}
    </div>
  )
}
