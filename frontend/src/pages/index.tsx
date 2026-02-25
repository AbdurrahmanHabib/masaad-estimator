import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-slate-200 flex flex-col items-center justify-center font-sans">
      <div className="max-w-md w-full p-8 bg-slate-950 border border-slate-900 rounded-lg shadow-2xl text-center">
        <div className="w-16 h-16 bg-emerald-500 rounded-sm flex items-center justify-center font-black text-black mx-auto mb-6 text-2xl">M</div>
        <h1 className="text-2xl font-black uppercase tracking-tighter mb-2 italic">Masaad_Estimator</h1>
        <p className="text-slate-600 text-[10px] font-mono mb-8 uppercase tracking-widest">Internal Engineering & Commercial Engine</p>
        
        <div className="space-y-4">
          <Link href="/estimate/new-project" className="block w-full py-4 bg-emerald-600 hover:bg-emerald-500 text-black font-bold uppercase text-xs tracking-widest rounded transition-all">
            Start_New_Estimation
          </Link>
          <button className="block w-full py-4 border border-slate-800 hover:border-slate-600 text-slate-400 font-bold uppercase text-[10px] tracking-widest rounded transition-all">
            View_Project_Archive
          </button>
        </div>
        
        <div className="mt-8 pt-8 border-t border-slate-900">
          <p className="text-slate-700 text-[9px] font-mono leading-relaxed">
            MADINAT AL SAADA ALUMINIUM & GLASS WORKS LLC<br/>
            AJMAN, UAE | PROD_v1.0
          </p>
        </div>
      </div>
    </div>
  );
}