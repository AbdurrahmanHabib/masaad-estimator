import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  LayoutDashboard, 
  FilePlus, 
  Archive, 
  Settings, 
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
    { name: 'Dashboard', icon: LayoutDashboard, href: '/' },
    { name: 'New Estimate', icon: FilePlus, href: '/estimate/new' },
    { name: 'Project Archive', icon: Archive, href: '/archive' },
    { name: 'Market Settings', icon: Settings, href: '/settings' },
  ];

  return (
    <div className="flex h-screen bg-ms-dark text-slate-200 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <div className={`${collapsed ? 'w-16' : 'w-64'} bg-ms-panel border-r border-ms-border flex flex-col transition-all duration-300 ease-in-out`}>
        <div className="p-4 border-b border-ms-border flex items-center justify-between">
          {!collapsed && (
            <div className="flex items-center gap-2 overflow-hidden">
              <div className="w-6 h-6 bg-ms-emerald rounded-sm flex items-center justify-center font-black text-black text-[10px] shrink-0">MS</div>
              <h1 className="text-[10px] font-black uppercase tracking-[0.2em] text-white truncate">Masaad Control</h1>
            </div>
          )}
          <button onClick={() => setCollapsed(!collapsed)} className="p-1.5 hover:bg-ms-slate-800 rounded transition-colors text-slate-400">
            {collapsed ? <Menu size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        <nav className="flex-1 p-2 space-y-1 mt-4">
          {navItems.map((item) => {
            const isActive = router.pathname === item.href;
            return (
              <Link 
                key={item.href} 
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all ${
                  isActive 
                    ? 'bg-ms-emerald/10 text-ms-emerald border border-ms-emerald/20 shadow-[0_0_15px_rgba(16,185,129,0.05)]' 
                    : 'text-slate-500 hover:bg-ms-slate-800 hover:text-slate-300'
                }`}
              >
                <item.icon size={16} className={isActive ? 'text-ms-emerald' : 'text-slate-500'} />
                {!collapsed && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="p-4 border-t border-ms-border">
            <p className="text-[7px] font-mono text-slate-600 uppercase tracking-widest text-center italic"> Madinat Al Saada Corp v2.5 </p>
          </div>
        )}
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* TOP BAR: Breadcrumbs & Rate */}
        <header className="h-12 bg-ms-panel/50 border-b border-ms-border flex items-center justify-between px-6 backdrop-blur-md">
          <div className="flex items-center gap-3 text-[9px] font-bold uppercase tracking-widest text-slate-500">
            <button onClick={() => router.back()} className="p-1 hover:bg-ms-slate-800 rounded transition-colors mr-2">
              <ArrowLeft size={14} />
            </button>
            <Link href="/" className="hover:text-white transition-colors">Home</Link>
            {pathParts.map((part, i) => (
              <React.Fragment key={i}>
                <ChevronRight size={10} className="text-slate-700" />
                <span className={i === pathParts.length - 1 ? "text-ms-emerald" : "hover:text-white transition-colors"}>
                  {part.replace(/-/g, '_')}
                </span>
              </React.Fragment>
            ))}
          </div>
          <div className="flex items-center gap-6">
            <div className="flex flex-col items-end">
              <span className="text-[7px] text-slate-600 uppercase font-black tracking-widest italic">Burdened_Shop_Rate</span>
              <span className="text-xs font-mono font-black text-ms-emerald tabular-nums tracking-tighter">AED 42.50/HR</span>
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