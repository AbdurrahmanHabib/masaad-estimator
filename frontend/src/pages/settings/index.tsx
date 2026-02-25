import React, { useState } from 'react';
import Link from 'next/link';
import { Upload, Users, Briefcase, Factory, TrendingUp, Settings2 } from 'lucide-react';

export default function SettingsDashboard() {
  const [marketVars, setMarketVars] = useState({ lmeRate: 2450.00, billetPremium: 450.00, stockLength: 6.0 });
  const [activeRates, setActiveRates] = useState({ trueShopRate: "0.00", totalAdmin: "0.00", loadedCatalogs: 0 });

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      {/* SIDEBAR */}
      <div className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between pt-1">
        <div>
          <div className="p-6 border-b border-slate-800 text-center">
            <img src="/logo.png" alt="Madinat Al Saada" className="h-16 mx-auto mb-4 object-contain" />
            <h1 className="text-sm font-bold uppercase tracking-widest text-white leading-tight">Madinat Al Saada</h1>
            <p className="text-[10px] text-ms-emerald font-mono mt-2 uppercase tracking-tighter">SaaS_TENANT_ADMIN</p>
          </div>
          <nav className="p-4 space-y-2">
            <Link href="/" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-all">
              Dashboard
            </Link>
            <Link href="/estimate/new" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-all">
              + New Estimate
            </Link>
            <Link href="/settings" className="block px-4 py-3 bg-ms-emerald/10 text-ms-emerald rounded border border-ms-emerald/20 text-xs font-bold uppercase tracking-wider shadow-inner">
              Market Settings
            </Link>
          </nav>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between px-10 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <Settings2 size={18} className="text-ms-emerald" />
            <h2 className="text-lg font-light tracking-wide text-slate-300 italic">Dynamic_Tenant_Control</h2>
          </div>
          <div className="flex items-center gap-6 text-[10px] font-mono text-slate-500 uppercase">
            <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-ms-emerald animate-pulse"></span> GLOBAL_SYNC: ACTIVE</span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-10 bg-slate-950">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
            
            {/* COLUMN 1: UPLOAD ZONES */}
            <div className="space-y-8">
              
              {/* ZONE 1: LABOR & PAYROLL */}
              <div className="bg-slate-900 border border-slate-800 p-6 shadow-2xl relative group overflow-hidden rounded-sm">
                <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Users size={14} className="text-ms-emerald" /> Zone 1: Labor & Payroll Engine
                  </h3>
                  <span className="text-[10px] font-mono text-ms-emerald bg-ms-emerald/10 px-2 py-1 rounded">True Shop Rate: AED {activeRates.trueShopRate}/hr</span>
                </div>
                <div className="border-2 border-dashed border-slate-800 hover:border-ms-emerald/50 bg-slate-950/50 p-8 text-center cursor-pointer transition-colors rounded-sm">
                  <Upload size={24} className="mx-auto text-slate-600 mb-3" />
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Upload Payroll .CSV</p>
                  <p className="text-[9px] text-slate-600 font-mono">Filters by 'FACTORY' to auto-calculate direct labor</p>
                </div>
              </div>

              {/* ZONE 2: OVERHEAD & P&L */}
              <div className="bg-slate-900 border border-slate-800 p-6 shadow-2xl relative group overflow-hidden rounded-sm">
                <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Briefcase size={14} className="text-ms-accent" /> Zone 2: Overhead & P&L
                  </h3>
                  <span className="text-[10px] font-mono text-ms-accent bg-ms-accent/10 px-2 py-1 rounded">Admin Pool: AED {activeRates.totalAdmin}</span>
                </div>
                <div className="border-2 border-dashed border-slate-800 hover:border-ms-accent/50 bg-slate-950/50 p-8 text-center cursor-pointer transition-colors rounded-sm">
                  <Upload size={24} className="mx-auto text-slate-600 mb-3" />
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Upload Admin Expenses .CSV</p>
                  <p className="text-[9px] text-slate-600 font-mono">Sums 'MADINAT' column for dynamic markup</p>
                </div>
              </div>

              {/* ZONE 3: SUPPLIER CATALOGS */}
              <div className="bg-slate-900 border border-slate-800 p-6 shadow-2xl relative group overflow-hidden rounded-sm">
                <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Factory size={14} className="text-ms-glass" /> Zone 3: Supplier Catalogs
                  </h3>
                  <span className="text-[10px] font-mono text-ms-glass bg-ms-glass/10 px-2 py-1 rounded">Catalogs Indexed: {activeRates.loadedCatalogs}</span>
                </div>
                <div className="border-2 border-dashed border-slate-800 hover:border-ms-glass/50 bg-slate-950/50 p-8 text-center cursor-pointer transition-colors rounded-sm">
                  <Upload size={24} className="mx-auto text-slate-600 mb-3" />
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Upload System Profiles .PDF</p>
                  <p className="text-[9px] text-slate-600 font-mono">Injects Ixx, Iyy, and Kg/m weights into Knowledge Graph</p>
                </div>
              </div>

            </div>

            {/* COLUMN 2: MARKET VARIABLES & SYSTEM STATUS */}
            <div className="space-y-8">
              {/* ZONE 4: MARKET VARIABLES */}
              <div className="bg-slate-900 border border-slate-800 p-8 shadow-2xl rounded-sm">
                <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2 mb-6 border-b border-slate-800 pb-3">
                  <TrendingUp size={14} className="text-white" /> Zone 4: Market Variables
                </h3>
                
                <div className="space-y-6">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Live LME Rate (USD/MT)</label>
                    <input 
                      type="number" 
                      value={marketVars.lmeRate} 
                      onChange={(e) => setMarketVars({...marketVars, lmeRate: parseFloat(e.target.value)})}
                      className="w-full bg-slate-950 border border-slate-800 text-ms-emerald font-mono p-3 rounded-sm focus:outline-none focus:border-ms-emerald"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Billet Premium Negotiation (USD/MT)</label>
                    <input 
                      type="number" 
                      value={marketVars.billetPremium} 
                      onChange={(e) => setMarketVars({...marketVars, billetPremium: parseFloat(e.target.value)})}
                      className="w-full bg-slate-950 border border-slate-800 text-white font-mono p-3 rounded-sm focus:outline-none focus:border-slate-600"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Standard Stock Length (Meters)</label>
                    <select 
                      value={marketVars.stockLength}
                      onChange={(e) => setMarketVars({...marketVars, stockLength: parseFloat(e.target.value)})}
                      className="w-full bg-slate-950 border border-slate-800 text-white font-mono p-3 rounded-sm focus:outline-none focus:border-slate-600"
                    >
                      <option value={5.8}>5.8m (Container Optimized)</option>
                      <option value={6.0}>6.0m (Standard Factory)</option>
                      <option value={6.5}>6.5m (Extended Span)</option>
                    </select>
                  </div>

                  <button className="w-full py-4 bg-slate-800 hover:bg-slate-700 text-white font-black uppercase text-[10px] tracking-[0.2em] transition-all rounded-sm border border-slate-700 mt-4">
                    Commit Market Variables To Database
                  </button>
                </div>
              </div>

              {/* SECURITY / ZERO-KNOWLEDGE WARNING */}
              <div className="bg-[#1e140a] border border-[#78350f] p-6 rounded-sm shadow-xl">
                <h4 className="text-[10px] font-black text-[#ea580c] uppercase tracking-widest mb-2">SaaS Architecture Directive Active</h4>
                <p className="text-[10px] font-mono text-[#fdba74] leading-relaxed opacity-80">
                  CRITICAL: The underlying engine currently contains zero hardcoded financial data. All calculations across the platform evaluate to <span className="font-bold text-[#f97316]">AED 0.00</span> until valid CSV payroll and expense structures are successfully injected via the zones above.
                </p>
              </div>

            </div>
          </div>
        </main>
      </div>
    </div>
  );
}