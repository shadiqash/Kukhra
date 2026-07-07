import client from './client'

// Auth
export const login = (username, password) =>
  client.post('/auth/token/', { username, password })
export const logout = (refresh) =>
  client.post('/auth/token/blacklist/', { refresh })

// Users
export const getUsers = () => client.get('/users/')
export const createUser = (data) => client.post('/users/', data)
export const updateUser = (id, data) => client.patch(`/users/${id}/`, data)

// Locations / Counters
export const getLocations = (params) => client.get('/locations/', { params })
export const getCounters = (params) => client.get('/counters/', { params })

// Products / Prices
export const getProducts = (params) => client.get('/products/', { params })
export const createProduct = (data) => client.post('/products/', data)
export const updateProduct = (id, data) => client.patch(`/products/${id}/`, data)
export const getPrices = (params) => client.get('/prices/', { params })
export const createPrice = (data) => client.post('/prices/', data)

// Customers / Suppliers
export const getCustomers = (params) => client.get('/customers/', { params })
export const createCustomer = (data) => client.post('/customers/', data)
export const updateCustomer = (id, data) => client.patch(`/customers/${id}/`, data)
export const getSuppliers = (params) => client.get('/suppliers/', { params })

// Lots
export const getLots = (params) => client.get('/lots/', { params })
export const createLot = (data) => client.post('/lots/', data)
export const updateLot = (id, data) => client.patch(`/lots/${id}/`, data)

// Processing
export const getProcessingRuns = (params) => client.get('/processing-runs/', { params })
export const createProcessingRun = (data) => client.post('/processing-runs/', data)

// Inventory
export const getMovements = (params) => client.get('/movements/', { params })
export const getStock = (params) => client.get('/stock/', { params })
export const getTransfers = (params) => client.get('/transfers/', { params })
export const createTransfer = (data) => client.post('/transfers/', data)
export const confirmTransferReceipt = (id) => client.post(`/transfers/${id}/confirm-receipt/`)
// Ledger convention: wastage removes stock, so quantities are recorded negative.
export const createWastage = ({ qty_kg, qty_pieces, ...data }) =>
  client.post('/movements/', {
    ...data,
    type: 'wastage',
    ...(qty_kg !== undefined && { qty_kg: -Math.abs(parseFloat(qty_kg) || 0) }),
    ...(qty_pieces !== undefined && { qty_pieces: -Math.abs(parseInt(qty_pieces, 10) || 0) }),
  })

// Procurement
export const getPurchaseOrders = (params) => client.get('/purchase-orders/', { params })
export const createPurchaseOrder = (data) => client.post('/purchase-orders/', data)
export const getGoodsReceived = (params) => client.get('/goods-received/', { params })
export const createGoodsReceived = (data) => client.post('/goods-received/', data)

// Sales sessions
export const getSessions = (params) => client.get('/sessions/', { params })
export const openSession = (data) => client.post('/sessions/', data)
export const closeSession = (id, data) => client.post(`/sessions/${id}/close/`, data)
export const getSessionSummary = (id) => client.get(`/sessions/${id}/summary/`)

// Orders
export const getOrders = (params) => client.get('/orders/', { params })
export const createOrder = (data) => client.post('/orders/', data)
export const fulfillOrder = (id) => client.post(`/orders/${id}/fulfill/`)
export const createOrderLine = (data) => client.post('/order-lines/', data)
export const createPayment = (data) => client.post('/payments/', data)

// Billing
export const getInvoices = (params) => client.get('/invoices/', { params })
export const createInvoice = (data) => client.post('/invoices/', data)
export const getCreditNotes = (params) => client.get('/credit-notes/', { params })

// Audit log
export const getAuditLogs = (params) => client.get('/audit-logs/', { params })

