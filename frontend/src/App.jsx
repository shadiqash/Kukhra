import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import LoginPage from './auth/LoginPage'
import PosScreen from './pos/PosScreen'
import AdminLayout from './admin/AdminLayout'
import Dashboard from './admin/Dashboard'
import Products from './admin/Products'
import Inventory from './admin/Inventory'
import StockOnHand from './admin/StockOnHand'
import Lots from './admin/Lots'
import Processing from './admin/Processing'
import Transfers from './admin/Transfers'
import Procurement from './admin/Procurement'
import Customers from './admin/Customers'
import Invoices from './admin/Invoices'
import SalesReports from './admin/SalesReports'
import CashReconciliation from './admin/CashReconciliation'
import Users from './admin/Users'
import AuditLog from './admin/AuditLog'
import Settings from './admin/Settings'
import WorkerLayout from './worker/WorkerLayout'
import LotArrival from './worker/LotArrival'
import FlockLog from './worker/FlockLog'
import ProcessingEntry from './worker/ProcessingEntry'
import ReceiveTransfer from './worker/ReceiveTransfer'
import Wastage from './worker/Wastage'

function RoleRoot() {
  const { user, isCashier, isWorker, isManager, isAdmin } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (isCashier()) return <Navigate to="/pos" replace />
  if (isWorker()) return <Navigate to="/worker/lot-arrival" replace />
  if (isManager() || isAdmin()) return <Navigate to="/admin" replace />
  return <Navigate to="/pos" replace />
}

function RequireAuth({ children, allow }) {
  const { user, hasRole } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (allow && !hasRole(...allow)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  const { user } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/" element={<RoleRoot />} />

      {/* POS — cashier, manager, superuser */}
      <Route
        path="/pos"
        element={
          <RequireAuth allow={['cashier', 'manager', 'outlet_manager', 'superuser']}>
            <PosScreen />
          </RequireAuth>
        }
      />

      {/* Admin — manager, outlet_manager, superuser */}
      <Route
        path="/admin"
        element={
          <RequireAuth allow={['manager', 'outlet_manager', 'superuser']}>
            <AdminLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="stock" element={<StockOnHand />} />
        <Route path="inventory" element={<Inventory />} />
        <Route path="lots" element={<Lots />} />
        <Route path="processing" element={<Processing />} />
        <Route path="transfers" element={<Transfers />} />
        <Route path="procurement" element={<Procurement />} />
        <Route path="customers" element={<Customers />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="reports" element={<SalesReports />} />
        <Route path="cash" element={<CashReconciliation />} />
        {/* superuser-only */}
        <Route path="users" element={<RequireAuth allow={['superuser']}><Users /></RequireAuth>} />
        <Route path="audit" element={<RequireAuth allow={['superuser']}><AuditLog /></RequireAuth>} />
        <Route path="settings" element={<RequireAuth allow={['superuser']}><Settings /></RequireAuth>} />
      </Route>

      {/* Worker PWA — warehouse, procurement */}
      <Route
        path="/worker"
        element={
          <RequireAuth allow={['warehouse', 'procurement']}>
            <WorkerLayout />
          </RequireAuth>
        }
      >
        <Route path="lot-arrival" element={<LotArrival />} />
        <Route path="flock-log" element={<FlockLog />} />
        <Route path="processing" element={<ProcessingEntry />} />
        <Route path="receive-transfer" element={<ReceiveTransfer />} />
        <Route
          path="wastage"
          element={
            <RequireAuth allow={['warehouse']}>
              <Wastage />
            </RequireAuth>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
