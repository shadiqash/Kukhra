import { openDB } from 'idb'

const DB_NAME = 'everfresh-pos'
const DB_VERSION = 1

function getDB() {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('pending_orders')) {
        db.createObjectStore('pending_orders', { keyPath: 'localId', autoIncrement: true })
      }
      if (!db.objectStoreNames.contains('products_cache')) {
        db.createObjectStore('products_cache', { keyPath: 'id' })
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
