import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-ms-bg flex flex-col relative overflow-hidden font-sans">
      {/* Navigation */}
      <nav className="h-20 bg-white/90 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-12 z-50">
        <div className="flex items-center gap-4">
          <img src="/logo.jpeg" alt="Logo" className="h-10 w-auto object-contain" />
          <div className="h-8 w-[1px] bg-slate-200"></div>
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-ms-primary leading-tight">
            Madinat Al Saada<br/>Aluminium & Glass
          </span>
        </div>
        
        <div className="hidden md:flex items-center gap-10">
          <Link href="#" className="nav-link">Dashboard</Link>
          <Link href="/estimate/new-project" className="nav-link text-ms-glass">New Estimate</Link>
          <Link href="#" className="nav-link">Project Archive</Link>
          <Link href="#" className="nav-link">Market Settings</Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex items-center justify-center p-6 relative">
        {/* Subtle Background Architectural Grid */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
             style={{ backgroundImage: 'linear-gradient(#2C3E50 1px, transparent 1px), linear-gradient(90deg, #2C3E50 1px, transparent 1px)', backgroundSize: '60px 60px' }}></div>

        <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 gap-12 items-center z-10">
          <div>
            <h1 className="text-5xl font-black text-ms-primary tracking-tighter leading-none mb-6">
              Precision <br/>
              <span className="text-ms-glass">Engineering</span> <br/>
              Platform.
            </h1>
            <p className="text-slate-500 text-sm leading-relaxed mb-10 max-w-sm">
              Enterprise-grade estimation engine for Madinat Al Saada. 
              Neuro-symbolic quantification, structural verification, and UAE market financial logic.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/estimate/new-project" className="px-8 py-4 bg-ms-primary text-white font-bold uppercase text-xs tracking-widest hover:bg-ms-dark transition-all shadow-xl shadow-ms-primary/20 text-center">
                Launch Estimator
              </Link>
              <button className="px-8 py-4 border border-ms-primary text-ms-primary font-bold uppercase text-xs tracking-widest hover:bg-ms-bg transition-all text-center">
                View Archive
              </button>
            </div>
          </div>

          <div className="hidden md:block">
            <div className="glass-panel p-8 rounded-sm rotate-2 shadow-2xl relative">
              <div className="absolute -top-4 -right-4 w-12 h-12 bg-ms-accent flex items-center justify-center text-white font-bold">
                v1.0
              </div>
              <div className="space-y-4 font-mono text-[10px] text-slate-400 uppercase tracking-widest">
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span>System_Status:</span>
                  <span className="text-emerald-500">Active</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span>Structural_Engine:</span>
                  <span className="text-ms-glass">ASCE 7-16</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span>Market_Lock:</span>
                  <span>AED/USD Fixed</span>
                </div>
                <div className="pt-4 text-slate-300 italic">
                  // Awaiting project ingestion...
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Subtle Architectural Credit Watermark */}
      <div className="absolute bottom-8 right-12 text-[9px] font-mono text-slate-300 uppercase tracking-[0.2em] select-none">
        System Architecture by <span className="text-slate-400 font-bold">Masaad</span>
      </div>

      <footer className="h-12 border-t border-slate-100 bg-white flex items-center justify-between px-12 text-[9px] font-bold text-slate-400 uppercase tracking-widest">
        <span>Madinat Al Saada Aluminium & Glass Works LLC</span>
        <span>Ajman, United Arab Emirates</span>
      </footer>
    </div>
  );
}