import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { usePageTitle } from '../hooks/usePageTitle';
import { getTodayBS } from '../utils/formatters';
import logoIcon from '../assets/logo-icon.png';
import { 
  LayoutGrid, Package, Layers, Boxes, ArrowRightLeft,
  Receipt, BarChart3, Box, Scissors,
  Truck, Users, UserCog, Clock, Settings, Wallet, LogOut
} from 'lucide-react';

const NAV = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutGrid },
  { to: '/admin/products', label: 'Products', icon: Package },
  { to: '/admin/stock', label: 'Stock on Hand', icon: Boxes },
  { to: '/admin/inventory', label: 'Stock Movements', icon: Layers },
  { to: '/admin/transfers', label: 'Transfers', icon: ArrowRightLeft },
  { to: '/admin/invoices', label: 'Invoices', icon: Receipt },
  { to: '/admin/reports', label: 'Sales Reports', icon: BarChart3 },
  { to: '/admin/cash', label: 'Cash & Shifts', icon: Wallet },
  { to: '/admin/lots', label: 'Lots', icon: Box },
  { to: '/admin/processing', label: 'Processing', icon: Scissors },
  { to: '/admin/procurement', label: 'Procurement', icon: Truck },
  { to: '/admin/customers', label: 'Customers', icon: Users },
  { to: '/admin/users', label: 'Users', icon: UserCog, adminOnly: true },
  { to: '/admin/audit', label: 'Audit Log', icon: Clock, adminOnly: true },
  { to: '/admin/settings', label: 'Settings', icon: Settings, adminOnly: true },
];

export default function AdminLayout() {
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();

  const currentNav = NAV.find(n => location.pathname.startsWith(n.to));
  const pageTitle = currentNav ? currentNav.label : 'Admin Portal';
  usePageTitle(pageTitle);

  return (
    <div className="flex h-screen w-full bg-brand-surface font-sans overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[240px] bg-brand-primary flex flex-col h-full flex-none">
        {/* Logo area */}
        <div className="px-5 py-6 border-b border-white/10 flex items-center gap-2">
          <img src={logoIcon} alt="" width="28" height="28" className="shrink-0" />
          <span className="text-white font-bold tracking-wide text-[16px]">Everfresh</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.filter((n) => !n.adminOnly || isAdmin()).map((n) => {
            const Icon = n.icon;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-2.5 rounded-lg mx-2 my-0.5 text-[14px] font-sans transition-colors ${
                    isActive 
                      ? 'bg-white/10 text-white font-semibold' 
                      : 'text-white/70 hover:bg-white/5 hover:text-white font-medium'
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
        <div className="p-4 border-t border-white/10 flex items-center justify-between mt-auto">
          <div className="text-white/70 text-[13px] truncate">
            {isAdmin() ? 'Admin' : 'Manager'} · {user?.username || 'admin'}
          </div>
          <button
            onClick={logout}
            className="text-white/60 hover:text-white p-1 rounded transition-colors"
            title="Sign Out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-white border-b-[1.5px] border-brand-border flex items-center justify-between px-6 shrink-0">
          <h1 className="text-text-primary font-bold text-[18px]">{pageTitle}</h1>
          <div className="text-text-secondary font-mono text-[13px]">
            {getTodayBS()}
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-brand-surface p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
