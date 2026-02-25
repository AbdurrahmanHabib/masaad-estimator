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
            <h1 className="text-sm font-bold uppercase tracking-widest text-white">Madinat Al Saada</h1>
            <p className="text-[10px] text-emerald-500 font-mono mt-1">ESTIMATOR PRO v1.0</p>
          </div>
          <nav className="p-4 space-y-2">
            <Link href="/" className="block px-4 py-3 bg-emerald-600/10 text-emerald-400 rounded border border-emerald-500/20 text-xs font-bold uppercase tracking-wider">
              Dashboard
            </Link>
            <Link href="/estimate/new" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-colors">
              + New Estimate
            </Link>
            <Link href="/archive" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-colors">
              Project Archive
            </Link>
            <Link href="/settings" className="block px-4 py-3 hover:bg-slate-800 text-slate-400 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-colors">
              Market Settings
            </Link>
          </nav>
        </div>
        <div className="p-4 border-t border-slate-800">
          <p className="text-[9px] text-slate-600 font-mono text-center uppercase tracking-widest">
            System Architecture by <br/><span className="text-slate-400 font-bold">Masaad</span>
          </p>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* TOP HEADER */}
        <header className="h-16 bg-slate-900/50 border-b border-slate-800 flex items-center justify-between px-8">
          <h2 className="text-lg font-light tracking-wide">Mission Control</h2>
          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> SYSTEM: ONLINE</span>
            <span>|</span>
            <span>LME Base: $2,450/MT</span>
          </div>
        </header>

        {/* DASHBOARD CONTENT */}
        <main className="flex-1 overflow-y-auto p-8 bg-slate-950">
          {/* Quick Stats Cards */}
          <div className="grid grid-cols-3 gap-6 mb-8">
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg shadow-lg">
              <h3 className="text-xs text-slate-500 uppercase tracking-widest mb-2">Active Estimates</h3>
              <p className="text-4xl font-mono text-white">4</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg shadow-lg">
              <h3 className="text-xs text-slate-500 uppercase tracking-widest mb-2">Pending Value (AED)</h3>
              <p className="text-4xl font-mono text-emerald-500">2.4M</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg shadow-lg">
              <h3 className="text-xs text-slate-500 uppercase tracking-widest mb-2">Processed Drawings</h3>
              <p className="text-4xl font-mono text-white">128</p>
            </div>
          </div>

          {/* Recent Activity Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-lg shadow-lg overflow-hidden">
            <div className="p-4 border-b border-slate-800 bg-slate-900/80">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">Recent Projects</h3>
            </div>
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950 text-slate-500 uppercase text-[10px] font-mono">
                <tr>
                  <th className="px-6 py-3">Project Ref</th>
                  <th className="px-6 py-3">Client</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                <tr className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-6 py-4 font-mono text-emerald-400">PRJ-KAB-001</td>
                  <td className="px-6 py-4 font-semibold text-slate-200">Al Kabir Tower</td>
                  <td className="px-6 py-4 text-slate-400 text-xs uppercase">INTL EXPORT</td>
                  <td className="px-6 py-4"><span className="px-2 py-1 bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 rounded text-[10px] uppercase tracking-wider">Processing</span></td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-xs text-emerald-500 hover:text-emerald-400 font-bold uppercase tracking-widest">Open</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </div>
  );
}