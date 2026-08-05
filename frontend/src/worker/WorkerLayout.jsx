import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { usePageTitle } from '../hooks/usePageTitle';
import { Truck, Bird, Scissors, ArrowRightLeft, Trash2, ClipboardList, LogOut } from 'lucide-react';
import logoIcon from '../assets/logo-icon.png';

const NAV = [
  { to: '/worker/lot-arrival', label: 'Arrival', icon: Truck },
  { to: '/worker/flock-log', label: 'Flock', icon: Bird },
  { to: '/worker/processing', label: 'Process', icon: Scissors },
  { to: '/worker/receive-transfer', label: 'Transfers', icon: ArrowRightLeft },
  // Wastage is warehouse-only: procurement can use the PWA but has no
  // inventory-movement access on the backend.
  { to: '/worker/wastage', label: 'Wastage', icon: Trash2, roles: ['warehouse'] },
  // Purchase orders are procurement-only: IsProcurementStaff excludes warehouse.
  { to: '/worker/purchase-orders', label: 'Orders', icon: ClipboardList, roles: ['procurement'] },
];

export default function WorkerLayout() {
  usePageTitle('Worker');
  const { user, logout } = useAuth();
  const location = useLocation();

  const nav = NAV.filter(n => !n.roles || n.roles.includes(user?.role));
  const currentNav = nav.find(n => location.pathname.startsWith(n.to));
  const pageTitle = currentNav ? currentNav.label : 'Worker Portal';

  return (
    <div className="flex flex-col md:flex-row h-[100dvh] w-full bg-brand-surface font-sans overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:flex-col w-[240px] bg-brand-primary h-full flex-none">
        <div className="px-5 py-6 border-b border-white/10 flex items-center gap-2">
          <img src={logoIcon} alt="" width="28" height="28" className="shrink-0" />
          <span className="text-white font-bold tracking-wide text-[16px]">Everfresh</span>
        </div>
        <nav className="flex-1 overflow-y-auto py-2">
          {nav.map((n) => {
            const Icon = n.icon;
            const isActive = location.pathname.startsWith(n.to);
            return (
              <NavLink
                key={n.to}
                to={n.to}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg mx-2 my-0.5 text-[14px] font-sans transition-colors ${
                  isActive ? 'bg-white/10 text-white font-semibold' : 'text-white/70 hover:bg-white/5 hover:text-white font-medium'
                }`}
              >
                <Icon size={18} />
                {n.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="p-4 border-t border-white/10 flex items-center justify-between mt-auto">
          <div className="text-white/70 text-[13px] truncate">{user?.username || 'worker'}</div>
          <button onClick={logout} className="text-white/60 hover:text-white p-1 rounded transition-colors" title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main column */}
      <div className="relative flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Mobile Top Header (sidebar replaces this on desktop) */}
        <header className="md:hidden h-14 bg-brand-primary flex items-center justify-between px-4 shrink-0 z-20 shadow-md">
          <div className="flex items-center gap-2">
            <img src={logoIcon} alt="" width="26" height="26" className="shrink-0" />
            <span className="text-white font-bold tracking-wide text-[16px]">Everfresh</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-white/80 text-[13px]">{user?.username || 'worker'}</span>
            <button onClick={logout} className="text-white/80 hover:text-white transition-colors" title="Logout">
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {/* Page Title Bar */}
        <div className="h-12 bg-white border-b-[1.5px] border-brand-border flex items-center px-4 md:px-6 shrink-0 z-10 shadow-sm">
          <h1 className="font-sans font-bold text-[18px] text-text-primary">{pageTitle}</h1>
        </div>

        {/* Main Content Scrollable Area */}
        <main className="flex-1 overflow-y-auto bg-brand-surface p-4 md:p-6 pb-24 md:pb-6">
          <Outlet />
        </main>

        {/* Mobile Bottom Navigation (sidebar replaces this on desktop) */}
        <nav className="md:hidden absolute bottom-0 w-full h-[72px] bg-white border-t-[1.5px] border-brand-border flex justify-between items-center px-2 pb-safe z-20 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          {nav.map((n) => {
            const Icon = n.icon;
            const isActive = location.pathname.startsWith(n.to);
            return (
              <NavLink
                key={n.to}
                to={n.to}
                className={`flex flex-col items-center justify-center flex-1 h-full gap-1 transition-colors ${
                  isActive ? 'text-brand-primary' : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <div className={`p-1.5 rounded-full ${isActive ? 'bg-[#f0faf8]' : 'bg-transparent'}`}>
                  <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
                </div>
                <span className={`text-[10px] font-sans ${isActive ? 'font-bold' : 'font-medium'}`}>
                  {n.label}
                </span>
              </NavLink>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
