import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  LayoutDashboard,
  Database,
  Settings,
  BarChart3,
  Search,
  Bell,
  ChevronRight,
  LogOut,
  ChevronLeft,
  Menu,
  Loader2,
  Archive,
  X,
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { apiGet } from '../lib/api';

interface LMEData {
  lme_price_usd?: number;
  price?: number;
}

const Layout = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const [mounted, setMounted] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pathParts, setPathParts] = useState<string[]>([]);

  const [lmePrice, setLmePrice] = useState<string | null>(null);
  const [lmeLoading, setLmeLoading] = useState(true);

  useEffect(() => {
    setMounted(true);
    setPathParts(router.asPath.split('/').filter(p => p));
  }, [router.asPath]);

  useEffect(() => {
    const fetchLiveRates = async () => {
      setLmeLoading(true);
      try {
        const lmeData = await apiGet<LMEData>('/api/settings/refresh-lme');
        const price = lmeData?.lme_price_usd ?? lmeData?.price;
        if (price !== undefined && price !== null) {
          setLmePrice(
            new Intl.NumberFormat('en-US', {
              style: 'currency',
              currency: 'USD',
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            }).format(price)
          );
        }
      } catch {
        // Non-fatal
      } finally {
        setLmeLoading(false);
      }
    };

    fetchLiveRates();
  }, []);

  // Close mobile sidebar on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [router.asPath]);

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, href: '/' },
    { name: 'New Estimate', icon: Database, href: '/estimate/new' },
    { name: 'Triage Queue', icon: Bell, href: '/triage' },
    { name: 'Settings', icon: Settings, href: '/settings' },
    { name: 'Archive', icon: Archive, href: '/archive' },
  ];

  const avatarLetter = user?.full_name?.charAt(0)?.toUpperCase() ?? 'U';
  const displayName = user?.full_name ?? user?.email ?? 'Unknown User';
  const displayRole = user?.role ?? 'Estimator';

  if (!mounted) return <div className="min-h-screen bg-[#f8fafc]" />;

  const sidebarContent = (
    <>
      {/* Company branding */}
      <div className="px-4 py-5 flex items-center gap-3 border-b border-white/10">
        <div className="w-9 h-9 rounded-md bg-[#d4a017] flex items-center justify-center text-[#002147] font-bold text-sm shrink-0">
          M
        </div>
        {(!collapsed || mobileOpen) && (
          <div className="flex flex-col min-w-0">
            <h1 className="text-[13px] font-bold text-[#d4a017] leading-tight tracking-wide">MASAAD</h1>
            <p className="text-[10px] text-white/70 font-medium leading-tight">Aluminium & Glass Works</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-5 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = router.pathname === item.href ||
            (item.href !== '/' && router.pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-[13px] font-medium transition-all ${
                isActive
                  ? 'bg-[#1e3a5f] text-white border-l-[3px] border-[#d4a017]'
                  : 'text-white/60 hover:bg-[#1e3a5f]/50 hover:text-white border-l-[3px] border-transparent'
              }`}
            >
              <item.icon size={18} className={isActive ? 'text-[#d4a017]' : 'text-white/50'} />
              {(!collapsed || mobileOpen) && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* User panel at bottom */}
      <div className="p-3 border-t border-white/10">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="w-8 h-8 bg-[#1e3a5f] rounded-md flex items-center justify-center text-[#d4a017] text-xs font-bold shrink-0 border border-[#d4a017]/30">
            {avatarLetter}
          </div>
          {(!collapsed || mobileOpen) && (
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{displayName}</p>
              <p className="text-[10px] text-white/50 truncate">{displayRole}</p>
            </div>
          )}
          {(!collapsed || mobileOpen) && (
            <button
              onClick={handleLogout}
              title="Log out"
              className="text-white/40 hover:text-red-400 transition-colors p-1"
            >
              <LogOut size={14} />
            </button>
          )}
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-[#f8fafc] text-[#1e293b] font-sans overflow-hidden">
      {/* MOBILE OVERLAY */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* MOBILE SIDEBAR */}
      <div
        className={`fixed inset-y-0 left-0 w-[240px] bg-[#002147] flex flex-col z-50 transform transition-transform duration-200 lg:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="absolute top-3 right-3">
          <button
            onClick={() => setMobileOpen(false)}
            className="p-1 text-white/60 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>
        {sidebarContent}
      </div>

      {/* DESKTOP SIDEBAR */}
      <div
        className={`${collapsed ? 'w-[68px]' : 'w-[240px]'} bg-[#002147] hidden lg:flex flex-col transition-all duration-200 z-50 print:hidden`}
      >
        {sidebarContent}
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* TOP HEADER BAR */}
        <header className="h-14 bg-white border-b border-[#e2e8f0] flex items-center justify-between px-6 z-30 print:hidden shadow-sm">
          <div className="flex items-center gap-4 flex-1">
            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(true)}
              className="p-1.5 hover:bg-slate-100 rounded-md transition-colors text-[#64748b] lg:hidden"
            >
              <Menu size={18} />
            </button>
            {/* Desktop collapse */}
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1.5 hover:bg-slate-100 rounded-md transition-colors text-[#64748b] hidden lg:block"
            >
              {collapsed ? <Menu size={18} /> : <ChevronLeft size={18} />}
            </button>

            {/* Breadcrumb */}
            <div className="flex items-center gap-1.5 text-xs text-[#64748b]">
              <Link href="/" className="hover:text-[#002147] transition-colors">Home</Link>
              {pathParts.map((part, i) => (
                <React.Fragment key={i}>
                  <ChevronRight size={10} className="text-[#e2e8f0]" />
                  <span className={i === pathParts.length - 1 ? "text-[#1e293b] font-medium" : "hover:text-[#002147] transition-colors"}>
                    {decodeURIComponent(part).replace(/-/g, ' ')}
                  </span>
                </React.Fragment>
              ))}
            </div>

            <div className="relative max-w-sm w-full ml-auto">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]" size={15} />
              <input
                type="text"
                placeholder="Search estimates..."
                className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md py-1.5 pl-9 pr-4 text-xs focus:ring-2 focus:ring-[#002147]/20 focus:border-[#002147] transition-all outline-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-4 ml-4">
            {/* LME Price */}
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-[#64748b] font-medium">LME Aluminium</span>
              {lmeLoading ? (
                <span className="text-xs text-[#64748b] flex items-center gap-1">
                  <Loader2 size={10} className="animate-spin" /> --
                </span>
              ) : (
                <span className="text-xs font-mono font-semibold text-[#002147]">{lmePrice || '$2,450.00'}</span>
              )}
            </div>

            <div className="h-6 w-px bg-[#e2e8f0]" />

            {/* User */}
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-xs font-medium text-[#1e293b] truncate max-w-[120px]">{displayName}</span>
              <span className="text-[10px] text-[#64748b]">{displayRole}</span>
            </div>

            <button
              onClick={handleLogout}
              title="Log out"
              className="p-1.5 hover:bg-red-50 rounded-md transition-colors text-[#64748b] hover:text-red-500"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="max-w-[1400px] mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
