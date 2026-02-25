import React from 'react';
import Link from 'next/link';

export default function Dashboard() {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden border-t-4 border-red-600">
      
      {/* SIDEBAR */}
      <div className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between">
        <div>
          <div className="p-6 border-b border-slate-800 text-center">
            <img src="/logo.png" alt="Madinat Al Saada" className="h-16 mx-auto mb-4 object-contain" />
            <h1 className="text-sm font-bold uppercase tracking-widest text-white leading-tight">Madinat Al Saada</h1>
            <p className="text-[10px] text-emerald-500 font-mono mt-2 uppercase tracking-tighter">ESTIMATOR_PRO_V2.0</p>
          </div>
          <nav className="p-4 space-y-2">
            <Link href="/" className="block px-4 py-3 bg-emerald-600/10 text-emerald-400 rounded border border-emerald-500/20 text-xs font-bold uppercase tracking-wider">
              Dashboard
            </Link>
            <Link href="/estimate/new" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-all">
              + New Estimate
            </Link>
          </nav>
        </div>
        <div className="p-6 border-t border-slate-800">
          <p className="text-[9px] text-slate-600 font-mono text-center uppercase tracking-[0.2em]">
            Architected by <br/><span className="text-slate-400 font-bold">Masaad</span>
          </p>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between px-10">
          <h2 className="text-lg font-light tracking-wide text-slate-300 italic">Industrial_Mission_Control</h2>
          <div className="flex items-center gap-6 text-[10px] font-mono text-slate-500 uppercase">
            <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_#10b981]"></span> CONNECTED</span>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-10 bg-slate-950 flex flex-col items-center justify-center">
           <h1 className="text-6xl font-black text-red-600 animate-pulse mb-4 italic uppercase tracking-tighter">System_Update_Pending</h1>
           <p className="text-slate-500 font-mono text-xs uppercase tracking-[0.5em]">Waiting for Railway Build Synchronization...</p>
           
           <div className="mt-12 w-full max-w-2xl bg-slate-900 border border-slate-800 p-8">
              <h3 className="text-[10px] font-bold text-emerald-500 uppercase mb-4 tracking-widest">// Latest_Deployment_Ref: 0DEF41A</h3>
              <div className="space-y-2 text-slate-400 font-mono text-[10px]">
                <p>&gt; Checking Tailwing compilation... [OK]</p>
                <p>&gt; Injecting Corporate Identity... [OK]</p>
                <p>&gt; Forcing Dark Mode override... [OK]</p>
              </div>
           </div>
        </main>
      </div>
    </div>
  );
}