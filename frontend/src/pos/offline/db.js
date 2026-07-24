import { openDB } from 'idb'

const DB_NAME = 'everfresh-pos'
const DB_VERSION = 2

function getDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('pending_orders')) {
        db.createObjectStore('pending_orders', { keyPath: 'localId', autoIncrement: true })
      }
      if (!db.objectStoreNames.contains('products_cache')) {
        db.createObjectStore('products_cache', { keyPath: 'id' })
      }
      // v2: held (parked) carts survive a refresh/crash instead of living only in
      // React state (EF-05). Keyed by a client-generated id so resume can delete
      // exactly the one that was resumed.
      if (!db.objectStoreNames.contains('held_orders')) {
        db.createObjectStore('held_orders', { keyPath: 'id' })
      }
    },
  })
}

export async function cachePendingOrder(order) {
  const db = await getDB()
  return db.add('pending_orders', { ...order, savedAt: Date.now() })
}

export async function getPendingOrders() {
  const db = await getDB()
  return db.getAll('pending_orders')
}

export async function deletePendingOrder(localId) {
  const db = await getDB()
  return db.delete('pending_orders', localId)
}

// Persists replay progress (e.g. a created-but-not-yet-fulfilled order id) so
// a later sync attempt resumes from where a partial failure left off, rather
// than re-running the atomic checkout and creating a duplicate order.
export async function updatePendingOrder(localId, patch) {
  const db = await getDB()
  const tx = db.transaction('pending_orders', 'readwrite')
  const existing = await tx.store.get(localId)
  if (existing) await tx.store.put({ ...existing, ...patch })
  await tx.done
}

// ── Held (parked) carts ───────────────────────────────────────────────────────
// Persisted so a rush of parked baskets is not wiped by a tablet reload, tab
// crash, or the auto-logout timer (EF-05).
export async function getHeldOrders() {
  const db = await getDB()
  return db.getAll('held_orders')
}

export async function putHeldOrder(held) {
  const db = await getDB()
  return db.put('held_orders', held)
}

export async function deleteHeldOrder(id) {
  const db = await getDB()
  return db.delete('held_orders', id)
}

export async function cacheProducts(products) {
  const db = await getDB()
  const tx = db.transaction('products_cache', 'readwrite')
  await Promise.all(products.map((p) => tx.store.put(p)))
  await tx.done
}

export async function getCachedProducts() {
  const db = await getDB()
  return db.getAll('products_cache')
}
