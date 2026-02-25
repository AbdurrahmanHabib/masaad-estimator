import React from 'react';
import Link from 'next/link';

export default function Dashboard() {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      
      {/* SIDEBAR */}
      <div className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between">
        <div>
          <div className="p-6 border-b border-slate-800 text-center">
            <img src="/logo.png" alt="Madinat Al Saada" className="h-16 mx-auto mb-4 object-contain" />
            <h1 className="text-sm font-bold uppercase tracking-widest text-white leading-tight">Madinat Al Saada<br/>Aluminium & Glass</h1>
            <p className="text-[10px] text-ms-emerald font-mono mt-2 uppercase tracking-tighter">ESTIMATOR_PRO_v2.5</p>
          </div>
          <nav className="p-4 space-y-2">
            <Link href="/" className="block px-4 py-3 bg-ms-emerald/10 text-ms-emerald rounded border border-ms-emerald/20 text-xs font-bold uppercase tracking-wider">
              Dashboard
            </Link>
            <Link href="/estimate/new" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-all border border-transparent hover:border-slate-700">
              + New Estimate
            </Link>
            <Link href="/archive" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-all border border-transparent hover:border-slate-700">
              Project Archive
            </Link>
            <Link href="/settings" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-all border border-transparent hover:border-slate-700">
              Market Settings
            </Link>
          </nav>
        </div>
        <div className="p-6 border-t border-slate-800">
          <p className="text-[9px] text-slate-600 font-mono text-center uppercase tracking-widest leading-relaxed">
            System Architecture by <br/><span className="text-slate-400 font-bold tracking-widest">MASAAD</span>
          </p>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* TOP HEADER */}
        <header className="h-16 bg-slate-900/50 border-b border-slate-800 flex items-center justify-between px-10">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-light tracking-wide text-slate-300 italic">Mission_Control</h2>
            <span className="px-2 py-0.5 bg-slate-800 text-[8px] font-bold text-slate-500 rounded uppercase tracking-widest">Operations_Centre_Ajman</span>
          </div>
          <div className="flex items-center gap-6 text-[10px] font-mono text-slate-500">
            <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-ms-emerald animate-pulse shadow-[0_0_10px_#10b981]"></span> SYSTEM: ONLINE</span>
            <span className="opacity-30">|</span>
            <span>LME_ALUM: <span className="text-white font-bold">$2,485.50/MT</span></span>
          </div>
        </header>

        {/* DASHBOARD CONTENT */}
        <main className="flex-1 overflow-y-auto p-10 bg-slate-950">
          {/* Global Efficiency Stats */}
          <div className="grid grid-cols-3 gap-8 mb-10">
            <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl relative group hover:border-ms-emerald/30 transition-all">
              <h3 className="text-[10px] text-slate-500 uppercase tracking-[0.2em] mb-4">Active Estimations</h3>
              <p className="text-5xl font-mono text-white tracking-tighter">04</p>
              <div className="absolute bottom-4 right-8 text-[8px] font-bold text-ms-emerald uppercase opacity-40 italic">Real-Time</div>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl relative group hover:border-ms-emerald/30 transition-all">
              <h3 className="text-[10px] text-slate-500 uppercase tracking-[0.2em] mb-4">Pending Pipeline (AED)</h3>
              <p className="text-5xl font-mono text-ms-emerald tracking-tighter">2.4M</p>
              <div className="absolute bottom-4 right-8 text-[8px] font-bold text-ms-emerald uppercase opacity-40 italic">Margin_Locked</div>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl relative group hover:border-ms-emerald/30 transition-all">
              <h3 className="text-[10px] text-slate-500 uppercase tracking-[0.2em] mb-4">Factory Efficiency</h3>
              <p className="text-5xl font-mono text-white tracking-tighter">96.8%</p>
              <div className="absolute bottom-4 right-8 text-[8px] font-bold text-ms-emerald uppercase opacity-40 italic">Scrap_Minimized</div>
            </div>
          </div>

          {/* Project Deployment Queue */}
          <div className="bg-slate-900 border border-slate-800 rounded-sm shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-slate-800 bg-slate-900/80 flex justify-between items-center">
              <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-300 italic">Project_Quantification_Queue</h3>
              <span className="text-[9px] font-bold text-slate-600 uppercase tracking-[0.3em]">Last Sync: {new Date().toLocaleTimeString()}</span>
            </div>
            <table className="w-full text-left">
              <thead className="bg-slate-950/50 text-slate-500 uppercase text-[9px] font-bold tracking-[0.1em]">
                <tr>
                  <th className="px-8 py-4">Project_Ref</th>
                  <th className="px-8 py-4">Primary_Client</th>
                  <th className="px-8 py-4">Region</th>
                  <th className="px-8 py-4">Status</th>
                  <th className="px-8 py-4 text-right">Verification</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 font-mono text-xs">
                <tr className="hover:bg-ms-emerald/[0.03] transition-colors group">
                  <td className="px-8 py-5 text-ms-emerald font-bold">PRJ-KAB-001</td>
                  <td className="px-8 py-5 text-slate-200 font-bold uppercase tracking-tight italic">Al Kabir Tower</td>
                  <td className="px-8 py-5 text-slate-500 uppercase tracking-tighter">Kabul_Afghanistan</td>
                  <td className="px-8 py-5">
                    <span className="px-3 py-1 bg-ms-emerald/10 text-ms-emerald border border-ms-emerald/20 text-[9px] font-black uppercase tracking-widest rounded-sm shadow-lg shadow-ms-emerald/5">In_Quantification</span>
                  </td>
                  <td className="px-8 py-5 text-right">
                    <Link href="/estimate/PRJ-KAB-001" className="text-[10px] bg-slate-800 hover:bg-ms-emerald px-5 py-2.5 text-slate-300 hover:text-black transition-all uppercase font-black tracking-tighter rounded-sm border border-slate-700 hover:border-ms-emerald">
                      Launch_Audit
                    </Link>
                  </td>
                </tr>
                {/* Additional Row for density */}
                <tr className="hover:bg-ms-emerald/[0.03] transition-colors opacity-40 group grayscale">
                  <td className="px-8 py-5 text-slate-500">PRJ-DXB-042</td>
                  <td className="px-8 py-5 text-slate-500 font-bold uppercase tracking-tight italic">Dubai Hills Villa</td>
                  <td className="px-8 py-5 text-slate-600 uppercase">Dubai_UAE</td>
                  <td className="px-8 py-5">
                    <span className="px-3 py-1 bg-slate-800 text-slate-600 text-[9px] font-bold uppercase tracking-widest rounded-sm">Completed</span>
                  </td>
                  <td className="px-8 py-5 text-right font-mono text-[9px]">Archive_Only</td>
                </tr>
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </div>
  );
}