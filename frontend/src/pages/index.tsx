import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-ms-dark text-slate-200 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Structural Grid Background Overlay */}
      <div className="absolute inset-0 opacity-5 pointer-events-none" 
           style={{ backgroundImage: 'radial-gradient(#10b981 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
      
      <div className="max-w-2xl w-full p-12 bg-ms-panel border border-slate-800 rounded-sm shadow-2xl text-center z-10">
        {/* Company Identity Header */}
        <div className="h-24 mx-auto mb-10 flex items-center justify-center bg-ms-emerald font-black text-ms-dark text-4xl rounded-sm w-24 shadow-lg shadow-emerald-500/20">
          MS
        </div>
        
        <h1 className="text-4xl font-black uppercase tracking-tighter mb-1 text-white italic">
          Madinat Al Saada
        </h1>
        <p className="text-ms-emerald font-mono text-xs font-bold tracking-[0.4em] mb-12 uppercase border-b border-slate-800 pb-4">
          Masaad Estimator v1.0 // Production_Build
        </p>

        <div className="grid grid-cols-1 gap-5">
          <Link href="/estimate/new-project" className="py-5 bg-ms-emerald hover:bg-emerald-500 text-black font-black uppercase text-sm tracking-widest transition-all rounded-sm shadow-lg shadow-emerald-500/10 text-center">
            [ Start New Estimation ]
          </Link>
          <button className="py-4 border border-slate-700 hover:border-ms-emerald hover:text-ms-emerald text-slate-500 font-bold uppercase text-[10px] tracking-widest transition-all rounded-sm">
            [ Project Archive ]
          </button>
        </div>

        <div className="mt-16 flex items-center justify-between text-[8px] font-mono text-slate-600 uppercase tracking-tighter">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 bg-ms-emerald rounded-full animate-pulse"></span> 
            Agent_Pipeline: Active
          </span>
          <span>Location: UAE_Operations</span>
          <span>Latencies: 45ms</span>
        </div>
      </div>

      {/* Subtle Architectural Credit Watermark */}
      <div className="absolute bottom-6 right-8 text-[9px] font-mono text-slate-700 uppercase tracking-[0.2em] select-none opacity-50">
        System Architecture by <span className="text-slate-500 font-bold">Masaad</span>
      </div>
    </div>
  );
}