import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { login as apiLogin, logout as apiLogout } from '../api'

const AuthContext = createContext(null)

function parseJwt(token) {
  try {
    return JSON.parse(atob(token.split('.')[1]))
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const access = localStorage.getItem('access')
    return access ? parseJwt(access) : null
  })

  const login = useCallback(async (username, password) => {
    const { data } = await apiLogin(username, password)
    localStorage.setItem('access', data.access)
    localStorage.setItem('refresh', data.refresh)
    setUser(parseJwt(data.access))
  }, [])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refresh')
    if (refresh) {
      try { await apiLogout(refresh) } catch { /* ignore */ }
    }
    localStorage.clear()
    setUser(null)
  }, [])

  // auto-logout when token expires
  useEffect(() => {
    if (!user) return
    const ms = user.exp * 1000 - Date.now() - 30_000
    if (ms <= 0) { logout(); return }
    const t = setTimeout(logout, ms)
    return () => clearTimeout(t)
  }, [user, logout])

  const hasRole = (...roles) => roles.includes(user?.role)
  const isCashier = () => hasRole('cashier')
  const isWorker = () => hasRole('warehouse', 'procurement')
  const isManager = () => hasRole('manager', 'outlet_manager', 'superuser')
  const isAdmin = () => hasRole('superuser')

  return (
    <AuthContext.Provider value={{ user, login, logout, hasRole, isCashier, isWorker, isManager, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
