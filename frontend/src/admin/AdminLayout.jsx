import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/products', label: 'Products' },
  { to: '/admin/inventory', label: 'Inventory' },
  { to: '/admin/lots', label: 'Lots' },
  { to: '/admin/processing', label: 'Processing' },
  { to: '/admin/transfers', label: 'Transfers' },
  { to: '/admin/procurement', label: 'Procurement' },
  { to: '/admin/customers', label: 'Customers' },
  { to: '/admin/invoices', label: 'Invoices' },
  { to: '/admin/reports', label: 'Sales Reports' },
  { to: '/admin/users', label: 'Users', adminOnly: true },
  { to: '/admin/audit', label: 'Audit Log', adminOnly: true },
  { to: '/admin/settings', label: 'Settings', adminOnly: true },
]

export default function AdminLayout() {
  const { user, logout, isAdmin } = useAuth()

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-4 border-b border-gray-100">
          <p className="font-bold text-green-700 text-sm">Everfresh</p>
          <p className="text-xs text-gray-500 mt-0.5">{user?.username}</p>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.filter((n) => !n.adminOnly || isAdmin()).map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm rounded-lg mx-2 mb-0.5 ${
                  isActive ? 'bg-green-50 text-green-700 font-semibold' : 'text-gray-600 hover:bg-gray-50'
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-100">
          <button
            onClick={logout}
            className="text-xs text-gray-500 hover:text-red-600 w-full text-left"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
