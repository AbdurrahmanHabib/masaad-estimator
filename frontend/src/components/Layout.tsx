import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  LayoutDashboard, 
  Database, 
  Maximize, 
  Settings, 
  BarChart3,
  Search,
  Bell,
  ChevronRight,
  ArrowLeft,
  LogOut,
  ChevronLeft,
  Menu
} from 'lucide-react';

const Layout = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [pathParts, setPathParts] = useState<string[]>([]);

  useEffect(() => {
    setMounted(true);
    setPathParts(router.asPath.split('/').filter(p => p));
  }, [router.asPath]);

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, href: '/' },
    { name: 'Ingestion', icon: Database, href: '/estimate/new' },
    { name: 'Optimization', icon: Maximize, href: '/optimization' },
    { name: 'Reports', icon: BarChart3, href: '/reports' },
    { name: 'Settings', icon: Settings, href: '/settings' },
  ];

  if (!mounted) return <div className="min-h-screen bg-[#f8fafc]" />;

  return (
    <div className="flex h-screen bg-[#f8fafc] text-slate-700 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <div className={`${collapsed ? 'w-20' : 'w-72'} bg-[#1e293b] flex flex-col transition-all duration-300 ease-in-out z-50 shadow-2xl`}>
        <div className="p-6 flex items-center gap-3 border-b border-slate-700/50">
          <img src="/logo.png" alt="Logo" className="w-10 h-10 object-contain shrink-0" />
          {!collapsed && (
            <div className="flex flex-col">
              <h1 className="text-sm font-black text-white leading-tight uppercase tracking-tighter">Madinat Al Saada</h1>
              <p className="text-[9px] text-emerald-400 font-bold uppercase tracking-widest">Estimator Pro</p>
            </div>
          )}
        </div>

        <nav className="flex-1 px-4 py-8 space-y-2">
          {navItems.map((item) => {
            const isActive = router.pathname === item.href;
            return (
              <Link 
                key={item.href} 
                href={item.href}
                className={`flex items-center gap-4 px-4 py-3.5 rounded-xl text-xs font-bold uppercase tracking-widest transition-all group ${
                  isActive 
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' 
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <item.icon size={20} className={isActive ? 'text-white' : 'text-slate-500 group-hover:text-slate-200'} />
                {!collapsed && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-700/50">
          <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-xl border border-slate-700/30">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-full flex items-center justify-center text-white font-black shadow-lg">A</div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-white truncate uppercase tracking-tighter">admin_control</p>
                <p className="text-[10px] text-slate-500 truncate font-medium uppercase tracking-widest">Master Tenant</p>
              </div>
            )}
            {!collapsed && <LogOut size={16} className="text-slate-500 hover:text-red-400 cursor-pointer transition-colors" />}
          </div>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* TOP HEADER */}
        <header className="h-20 bg-white border-b border-slate-200 flex items-center justify-between px-10 shadow-sm z-40">
          <div className="flex items-center gap-8 flex-1">
            <div className="flex items-center gap-4">
              <button onClick={() => router.back()} className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-400">
                <ArrowLeft size={20} />
              </button>
              <div className="flex flex-col">
                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                  <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
                  {pathParts.map((part, i) => (
                    <React.Fragment key={i}>
                      <ChevronRight size={12} className="text-slate-300" />
                      <span className={i === pathParts.length - 1 ? "text-blue-600" : "hover:text-blue-600 transition-colors"}>
                        {part.replace(/-/g, '_').toUpperCase()}
                      </span>
                    </React.Fragment>
                  ))}
                </div>
                <h2 className="text-lg font-black text-slate-800 uppercase tracking-tighter mt-0.5">
                  {router.pathname === '/' ? 'Operational Dashboard' : router.pathname.split('/').pop()?.replace(/-/g, ' ')}
                </h2>
              </div>
            </div>
            
            <div className="relative max-w-md w-full ml-10">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
              <input 
                type="text" 
                placeholder="Search Group Data..." 
                className="w-full bg-slate-50 border border-slate-200 rounded-xl py-2.5 pl-12 pr-4 text-xs font-medium focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all outline-none"
              />
            </div>
          </div>
          
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-6">
              <div className="flex flex-col items-end">
                <span className="text-[8px] text-slate-400 uppercase font-black tracking-widest italic">Live_Shop_Rate</span>
                <span className="text-sm font-mono font-black text-emerald-600 tabular-nums">AED 48.75/HR</span>
              </div>
              <div className="h-8 w-[1px] bg-slate-200"></div>
              <div className="flex flex-col items-end">
                <span className="text-[8px] text-slate-400 uppercase font-black tracking-widest italic">LME_Aluminum</span>
                <span className="text-sm font-mono font-black text-slate-800 tabular-nums">$2,450.00</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="relative cursor-pointer hover:bg-slate-100 p-2.5 rounded-xl transition-colors group">
                <Bell size={22} className="text-slate-500 group-hover:text-blue-600" />
                <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 bg-red-500 border-2 border-white rounded-full"></span>
              </div>
              <button onClick={() => setCollapsed(!collapsed)} className="p-2.5 hover:bg-slate-100 rounded-xl transition-colors text-slate-500 hover:text-blue-600">
                {collapsed ? <Menu size={22} /> : <ChevronLeft size={22} />}
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-10">
          <div className="max-w-[1600px] mx-auto animate-in fade-in duration-500">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;