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
  ArrowLeft,
  LogOut,
  ChevronLeft,
  Menu,
  Loader2
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
  const [pathParts, setPathParts] = useState<string[]>([]);

  const [lmePrice, setLmePrice] = useState<string | null>(null);
  const [lmeLoading, setLmeLoading] = useState(true);

  useEffect(() => {
    setMounted(true);
    setPathParts(router.asPath.split('/').filter(p => p));
  }, [router.asPath]);

  // Fetch live LME price on mount (skip /api/settings to avoid 404)
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
        // Non-fatal -- keep null, UI will show fallback
      } finally {
        setLmeLoading(false);
      }
    };

    fetchLiveRates();
  }, []);

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, href: '/' },
    { name: 'Ingestion', icon: Database, href: '/estimate/new' },
    { name: 'Reports', icon: BarChart3, href: '/reports' },
    { name: 'Triage', icon: Bell, href: '/triage' },
    { name: 'Settings', icon: Settings, href: '/settings' },
  ];

  const avatarLetter = user?.full_name?.charAt(0)?.toUpperCase() ?? 'U';
  const displayName = user?.full_name ?? user?.email ?? 'Unknown User';
  const displayRole = user?.role ?? 'User';

  if (!mounted) return <div className="min-h-screen bg-[#f8fafc]" />;

  return (
    <div className="flex h-screen bg-[#f8fafc] text-slate-700 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <div className={`${collapsed ? 'w-16' : 'w-60'} bg-slate-900 flex flex-col transition-all duration-200 z-50 print:hidden`}>
        <div className="p-4 flex items-center gap-3 border-b border-slate-800">
          <img src="/logo.png" alt="Logo" className="w-8 h-8 object-contain shrink-0" />
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <h1 className="text-sm font-bold text-white leading-tight truncate">Madinat Al Saada</h1>
              <p className="text-[10px] text-slate-400 font-medium">Estimator</p>
            </div>
          )}
        </div>

        <nav className="flex-1 px-3 py-6 space-y-1">
          {navItems.map((item) => {
            const isActive = router.pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <item.icon size={18} className={isActive ? 'text-white' : 'text-slate-500'} />
                {!collapsed && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {/* User panel */}
        <div className="p-3 border-t border-slate-800">
          <div className="flex items-center gap-3 p-2">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0">
              {avatarLetter}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate">{displayName}</p>
                <p className="text-[10px] text-slate-500 truncate">{displayRole}</p>
              </div>
            )}
            {!collapsed && (
              <button
                onClick={handleLogout}
                title="Log out"
                className="text-slate-500 hover:text-red-400 transition-colors"
              >
                <LogOut size={14} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* TOP HEADER */}
        <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-40 print:hidden">
          <div className="flex items-center gap-4 flex-1">
            <button onClick={() => setCollapsed(!collapsed)} className="p-1.5 hover:bg-slate-100 rounded-md transition-colors text-slate-400">
              {collapsed ? <Menu size={18} /> : <ChevronLeft size={18} />}
            </button>

            {/* Breadcrumb */}
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
              {pathParts.map((part, i) => (
                <React.Fragment key={i}>
                  <ChevronRight size={10} className="text-slate-300" />
                  <span className={i === pathParts.length - 1 ? "text-slate-600 font-medium" : "hover:text-blue-600 transition-colors"}>
                    {decodeURIComponent(part).replace(/-/g, ' ')}
                  </span>
                </React.Fragment>
              ))}
            </div>

            <div className="relative max-w-sm w-full ml-auto">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
              <input
                type="text"
                placeholder="Search..."
                className="w-full bg-slate-50 border border-slate-200 rounded-md py-1.5 pl-9 pr-4 text-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all outline-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-4 ml-4">
            {/* LME Price */}
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-slate-400">LME Aluminium</span>
              {lmeLoading ? (
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <Loader2 size={10} className="animate-spin" /> --
                </span>
              ) : (
                <span className="text-xs font-mono font-medium text-slate-700">{lmePrice || '$2,450.00'}</span>
              )}
            </div>

            <div className="h-6 w-px bg-slate-200" />

            {/* User */}
            <div className="flex flex-col items-end">
              <span className="text-xs font-medium text-slate-700 truncate max-w-[120px]">{displayName}</span>
              <span className="text-[10px] text-slate-400">{displayRole}</span>
            </div>

            <button
              onClick={handleLogout}
              title="Log out"
              className="p-1.5 hover:bg-red-50 rounded-md transition-colors text-slate-400 hover:text-red-500"
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
