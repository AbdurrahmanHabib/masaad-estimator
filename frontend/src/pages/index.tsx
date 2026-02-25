import React from 'react';
import Link from 'next/link';

export default function Dashboard() {
  return (
    <div className="flex-1 overflow-y-auto p-10 bg-ms-dark">
      {/* Global Efficiency Stats */}
      <div className="grid grid-cols-3 gap-8 mb-10">
        <div className="bg-ms-panel border border-ms-border p-8 rounded-sm shadow-2xl relative group hover:border-ms-emerald/30 transition-all">
          <h3 className="text-[10px] text-slate-500 uppercase tracking-[0.2em] mb-4">Active Estimations</h3>
          <p className="text-5xl font-mono text-white tracking-tighter">04</p>
          <div className="absolute bottom-4 right-8 text-[8px] font-bold text-ms-emerald uppercase opacity-40 italic">Real-Time</div>
        </div>
        <div className="bg-ms-panel border border-ms-border p-8 rounded-sm shadow-2xl relative group hover:border-ms-emerald/30 transition-all">
          <h3 className="text-[10px] text-slate-500 uppercase tracking-[0.2em] mb-4">Pending Pipeline (AED)</h3>
          <p className="text-5xl font-mono text-ms-emerald tracking-tighter">2.4M</p>
          <div className="absolute bottom-4 right-8 text-[8px] font-bold text-ms-emerald uppercase opacity-40 italic">Margin_Locked</div>
        </div>
        <div className="bg-ms-panel border border-ms-border p-8 rounded-sm shadow-2xl relative group hover:border-ms-emerald/30 transition-all">
          <h3 className="text-[10px] text-slate-500 uppercase tracking-[0.2em] mb-4">Factory Efficiency</h3>
          <p className="text-5xl font-mono text-white tracking-tighter">96.8%</p>
          <div className="absolute bottom-4 right-8 text-[8px] font-bold text-ms-emerald uppercase opacity-40 italic">Scrap_Minimized</div>
        </div>
      </div>

      {/* Project Deployment Queue */}
      <div className="bg-ms-panel border border-ms-border rounded-sm shadow-2xl overflow-hidden">
        <div className="p-5 border-b border-ms-border bg-ms-panel/80 flex justify-between items-center">
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-300 italic">Project_Quantification_Queue</h3>
          <span className="text-[9px] font-bold text-slate-600 uppercase tracking-[0.3em]">Last Sync: {new Date().toLocaleTimeString()}</span>
        </div>
        <table className="w-full text-left">
          <thead className="bg-ms-dark/50 text-slate-500 uppercase text-[9px] font-bold tracking-[0.1em]">
            <tr>
              <th className="px-8 py-4">Project_Ref</th>
              <th className="px-8 py-4">Primary_Client</th>
              <th className="px-8 py-4">Region</th>
              <th className="px-8 py-4">Status</th>
              <th className="px-8 py-4 text-right">Verification</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ms-border/50 font-mono text-xs">
            <tr className="hover:bg-ms-emerald/[0.03] transition-colors group">
              <td className="px-8 py-5 text-ms-emerald font-bold">PRJ-KAB-001</td>
              <td className="px-8 py-5 text-slate-200 font-bold uppercase tracking-tight italic">Al Kabir Tower</td>
              <td className="px-8 py-5 text-slate-500 uppercase tracking-tighter">Kabul_Afghanistan</td>
              <td className="px-8 py-5">
                <span className="px-3 py-1 bg-ms-emerald/10 text-ms-emerald border border-ms-emerald/20 text-[9px] font-black uppercase tracking-widest rounded-sm shadow-lg shadow-ms-emerald/5">In_Quantification</span>
              </td>
              <td className="px-8 py-5 text-right">
                <Link href="/estimate/PRJ-KAB-001" className="text-[10px] bg-ms-border hover:bg-ms-emerald px-5 py-2.5 text-slate-300 hover:text-black transition-all uppercase font-black tracking-tighter rounded-sm border border-ms-border hover:border-ms-emerald">
                  Launch_Audit
                </Link>
              </td>
            </tr>
            <tr className="hover:bg-ms-emerald/[0.03] transition-colors opacity-40 group grayscale">
              <td className="px-8 py-5 text-slate-500">PRJ-DXB-042</td>
              <td className="px-8 py-5 text-slate-500 font-bold uppercase tracking-tight italic">Dubai Hills Villa</td>
              <td className="px-8 py-5 text-slate-600 uppercase">Dubai_UAE</td>
              <td className="px-8 py-5">
                <span className="px-3 py-1 bg-ms-border text-slate-600 text-[9px] font-bold uppercase tracking-widest rounded-sm">Completed</span>
              </td>
              <td className="px-8 py-5 text-right font-mono text-[9px]">Archive_Only</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}