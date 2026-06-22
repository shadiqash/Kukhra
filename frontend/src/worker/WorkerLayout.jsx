import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const NAV = [
  { to: '/worker/lot-arrival', label: 'Lot Arrival' },
  { to: '/worker/flock-log', label: 'Flock Log' },
  { to: '/worker/processing', label: 'Processing Entry' },
  { to: '/worker/receive-transfer', label: 'Receive Transfer' },
  { to: '/worker/wastage', label: 'Wastage' },
]

export default function WorkerLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-green-700 text-white px-4 py-3 flex items-center">
        <span className="font-bold flex-1">Everfresh Worker</span>
        <span className="text-sm opacity-80 mr-4">{user?.username}</span>
        <button onClick={logout} className="text-xs opacity-70 hover:opacity-100">Sign out</button>
      </header>
      <nav className="bg-white border-b border-gray-200 flex overflow-x-auto">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `flex-shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition ${
                isActive
                  ? 'border-green-600 text-green-700'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`
            }
          >
            {n.label}
          </NavLink>
        ))}
      </nav>
      <main className="flex-1 p-4 max-w-lg mx-auto w-full">
        <Outlet />
      </main>
    </div>
  )
}
