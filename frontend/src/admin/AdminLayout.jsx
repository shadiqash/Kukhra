import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { usePageTitle } from '../hooks/usePageTitle';
import { useTheme } from '../hooks/useTheme';
import { getTodayBS } from '../utils/formatters';
import logoIcon from '../assets/logo-icon.png';
import {
  LayoutGrid, Package, Layers, Boxes, ArrowRightLeft,
  Receipt, BarChart3, Box, Scissors,
  Truck, Users, UserCog, Clock, Settings, Wallet, LogOut, Menu, X, ShoppingCart, Sun, Moon
} from 'lucide-react';

const NAV = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutGrid },
  { to: '/pos', label: 'Point of Sale (POS)', icon: ShoppingCart },
  { to: '/admin/products', label: 'Products', icon: Package },
  { to: '/admin/stock', label: 'Stock on Hand', icon: Boxes },
  { to: '/admin/inventory', label: 'Stock Movements', icon: Layers },
  { to: '/admin/transfers', label: 'Transfers', icon: ArrowRightLeft },
  { to: '/admin/invoices', label: 'Invoices', icon: Receipt },
  { to: '/admin/reports', label: 'Sales Reports', icon: BarChart3 },
  { to: '/admin/cash', label: 'Cash & Shifts', icon: Wallet },
  // Backend restricts these to warehouse/procurement/manager/superuser
  // (IsLotStaff / IsProcurementStaff in apps/accounts/permissions.py) — outlet
  // managers get a 403 from every one of these endpoints, so the nav must not
  // offer them here.
  { to: '/admin/lots', label: 'Lots', icon: Box, hideForOutletManager: true },
  { to: '/admin/processing', label: 'Processing', icon: Scissors, hideForOutletManager: true },
  { to: '/admin/procurement', label: 'Procurement', icon: Truck, hideForOutletManager: true },
  { to: '/admin/customers', label: 'Customers', icon: Users },
  { to: '/admin/users', label: 'Users', icon: UserCog, adminOnly: true },
  { to: '/admin/audit', label: 'Audit Log', icon: Clock, adminOnly: true },
  { to: '/admin/settings', label: 'Settings', icon: Settings, adminOnly: true },
];

export default function AdminLayout() {
  const { user, logout, isAdmin, hasRole } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();
  // Mobile-only nav drawer; the sidebar is always visible from md up.
  const [menuOpen, setMenuOpen] = useState(false);

  const currentNav = NAV.find(n => location.pathname.startsWith(n.to));
  const pageTitle = currentNav ? currentNav.label : 'Admin Portal';
  usePageTitle(pageTitle);

  return (
    <div className="flex h-screen w-full bg-background font-sans overflow-hidden transition-colors duration-300">
      {/* Backdrop for the mobile drawer */}
      {menuOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setMenuOpen(false)}
        />
      )}

      {/* Sidebar — static from md up, slide-in drawer on mobile */}
      <aside className={`w-[260px] glass-dark flex-col h-full flex-none md:flex md:static transition-all duration-300 shadow-2xl z-50 ${
        menuOpen ? 'flex fixed inset-y-0 left-0' : '-translate-x-full fixed md:translate-x-0 md:static'
      }`}>
        {/* Logo area */}
        <div className="px-6 py-7 border-b border-white/10 flex items-center gap-3">
          <img src={logoIcon} alt="" width="32" height="32" className="shrink-0 drop-shadow-md" />
          <span className="text-white font-bold tracking-wide text-lg drop-shadow-sm">Everfresh</span>
          <button
            onClick={() => setMenuOpen(false)}
            className="ml-auto text-white/70 hover:text-white md:hidden p-1 rounded-md hover:bg-white/10 transition-colors"
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1 custom-scrollbar">
          {NAV.filter((n) => (!n.adminOnly || isAdmin()) && (!n.hideForOutletManager || !hasRole('outlet_manager'))).map((n) => {
            const Icon = n.icon;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-xl mx-2 text-[14px] font-sans transition-all duration-200 ${
                    isActive 
                      ? 'bg-gradient-to-r from-white/20 to-white/5 text-white font-semibold shadow-inner scale-[1.02]' 
                      : 'text-white/70 hover:bg-white/10 hover:text-white font-medium hover:scale-[1.02]'
                  }`
                }
              >
                <Icon size={18} />
                {n.label}
              </NavLink>
            );
          })}
        </nav>

        {/* User area */}
        <div className="p-4 border-t border-white/10 flex flex-col gap-3 mt-auto">
          <div className="flex items-center justify-between">
            <div className="text-white/70 text-[13px] truncate">
              {isAdmin() ? 'Admin' : 'Manager'} · <span className="text-white font-medium">{user?.username || 'admin'}</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={toggleTheme}
                className="text-white/60 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Toggle Theme"
              >
                {isDark ? <Sun size={18} /> : <Moon size={18} />}
              </button>
              <button
                onClick={logout}
                className="text-white/60 hover:text-white p-2 rounded-lg hover:bg-white/10 transition-colors"
                title="Sign Out"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 relative z-10 h-full">
        {/* Top bar */}
        <header className="h-[72px] bg-surface/80 backdrop-blur-md border-b border-border flex items-center justify-between px-6 shrink-0 shadow-sm z-20 transition-colors">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setMenuOpen(true)}
              className="text-text-secondary hover:text-text-primary hover:bg-surface-hover p-2 rounded-lg md:hidden transition-colors"
              aria-label="Open menu"
            >
              <Menu size={24} />
            </button>
            <h1 className="text-text-primary font-bold text-xl tracking-tight">{pageTitle}</h1>
          </div>
          <div className="hidden sm:flex items-center gap-4">
            <div className="text-text-secondary font-mono text-sm bg-surface-hover px-4 py-1.5 rounded-full border border-border">
              {getTodayBS()}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 relative">
          <div className="animate-fade-in max-w-7xl mx-auto h-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
