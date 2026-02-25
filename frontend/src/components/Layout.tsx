import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  Home, 
  Database, 
  Maximize, 
  Settings, 
  BarChart,
  ChevronRight, 
  ArrowLeft,
  Menu,
  ChevronLeft
} from 'lucide-react';

const Layout = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const pathParts = router.asPath.split('/').filter(p => p);

  const navItems = [
    { name: 'Home', icon: Home, href: '/' },
    { name: 'Ingestion', icon: Database, href: '/estimate/new' },
    { name: 'Optimization', icon: Maximize, href: '/optimization' },
    { name: 'Reports', icon: BarChart, href: '/reports' },
    { name: 'Settings', icon: Settings, href: '/settings' },
  ];

  return (
    <div className="flex h-screen bg-[#0f172a] text-slate-200 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <div className={`${collapsed ? 'w-16' : 'w-64'} bg-[#1e293b] border-r border-slate-800 flex flex-col transition-all duration-300 ease-in-out z-50 shadow-2xl`}>
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          {!collapsed ? (
            <div className="flex items-center gap-3 overflow-hidden">
              <img src="/logo.png" alt="Madinat Logo" className="w-8 h-8 object-contain shrink-0" />
              <div className="flex flex-col">
                <h1 className="text-[10px] font-black uppercase tracking-[0.2em] text-white truncate">Madinat Al Saada</h1>
                <p className="text-[7px] text-ms-emerald font-bold uppercase tracking-tighter">Estimator_Pro_v2.5</p>
              </div>
            </div>
          ) : (
            <img src="/logo.png" alt="Logo" className="w-8 h-8 object-contain mx-auto" />
          )}
          <button onClick={() => setCollapsed(!collapsed)} className="p-1.5 hover:bg-ms-dark rounded transition-colors text-slate-400 absolute -right-3 top-10 bg-[#1e293b] border border-slate-800 rounded-full">
            {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
          </button>
        </div>

        <nav className="flex-1 p-3 space-y-1 mt-6">
          {navItems.map((item) => {
            const isActive = router.pathname === item.href;
            return (
              <Link 
                key={item.href} 
                href={item.href}
                className={`flex items-center gap-3 px-3 py-3 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all group ${
                  isActive 
                    ? 'bg-ms-emerald/10 text-ms-emerald border border-ms-emerald/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]' 
                    : 'text-slate-400 hover:bg-ms-dark hover:text-slate-200'
                }`}
              >
                <item.icon size={18} className={isActive ? 'text-ms-emerald' : 'text-slate-500 group-hover:text-slate-300'} />
                {!collapsed && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="p-4 border-t border-slate-800 bg-[#0f172a]/20">
            <p className="text-[7px] font-mono text-slate-600 uppercase tracking-widest text-center italic"> Madinat Al Saada Aluminium & Glass </p>
          </div>
        )}
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* TOP BAR: Breadcrumbs & Rate */}
        <header className="h-14 bg-[#0f172a]/80 border-b border-slate-800 flex items-center justify-between px-8 backdrop-blur-md z-40">
          <div className="flex items-center gap-4 text-[9px] font-bold uppercase tracking-widest text-slate-500">
            <button onClick={() => router.back()} className="p-1.5 hover:bg-[#1e293b] rounded transition-colors mr-2 text-slate-400">
              <ArrowLeft size={14} />
            </button>
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            {pathParts.map((part, i) => (
              <React.Fragment key={i}>
                <ChevronRight size={10} className="text-slate-700" />
                <span className={i === pathParts.length - 1 ? "text-ms-emerald" : "hover:text-white transition-colors"}>
                  {part.replace(/-/g, '_').toUpperCase()}
                </span>
              </React.Fragment>
            ))}
          </div>
          <div className="flex items-center gap-8">
            <div className="flex flex-col items-end">
              <span className="text-[7px] text-slate-600 uppercase font-black tracking-widest italic">Live_Burdened_Shop_Rate</span>
              <span className="text-sm font-mono font-black text-ms-emerald tabular-nums tracking-tighter">AED 48.75/HR</span>
            </div>
            <div className="h-8 w-[1px] bg-slate-800"></div>
            <div className="flex flex-col items-end">
              <span className="text-[7px] text-slate-600 uppercase font-black tracking-widest italic">LME_Aluminum_Ref</span>
              <span className="text-sm font-mono font-black text-white tabular-nums tracking-tighter">$2,450.00/MT</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;