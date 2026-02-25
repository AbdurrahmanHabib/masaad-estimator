import React from 'react';
import { Scissors, Layout, AlertTriangle, CheckCircle2 } from 'lucide-react';

const OptimizationVisuals = ({ scrap_pct }: { scrap_pct: number }) => {
  const isWasteViolation = scrap_pct > 5;

  return (
    <div className="bg-slate-900 border border-slate-800 p-8 shadow-2xl rounded-sm mt-10">
      <div className="flex justify-between items-center mb-10 border-b border-slate-800 pb-4">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white italic flex items-center gap-3">
          <Scissors size={16} className="text-ms-emerald" /> Nesting_Efficiency_Analytics
        </h3>
        <div className={`px-3 py-1 rounded-sm border ${isWasteViolation ? 'bg-red-500/10 border-red-500/30' : 'bg-ms-emerald/10 border-ms-emerald/30'}`}>
            <span className={`text-[9px] font-black uppercase ${isWasteViolation ? 'text-red-500' : 'text-ms-emerald'}`}>
                Waste_Report: {scrap_pct}%
            </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* 1D ALUMINUM NESTING */}
        <div className="space-y-4">
          <div className="flex justify-between text-[9px] font-bold text-slate-500 uppercase tracking-widest">
            <span>Linear_Aluminum_Bin_Packing</span>
            <span className="text-white font-mono tracking-tighter">Engine: CP-SAT</span>
          </div>
          <div className="h-8 bg-slate-950 border border-slate-800 rounded-sm flex overflow-hidden shadow-inner">
            <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '45%' }}></div>
            <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '30%' }}></div>
            <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '20%' }}></div>
            <div className="h-full bg-red-900/40 flex-1"></div>
          </div>
        </div>

        {/* 2D ACP NESTING */}
        <div className="space-y-4">
          <div className="flex justify-between text-[9px] font-bold text-slate-500 uppercase tracking-widest">
            <span>ACP_Sheet_Nesting_Map</span>
            <span className="text-white font-mono tracking-tighter">50mm_Fold_Lock ✓</span>
          </div>
          <div className="aspect-video bg-slate-950 border border-slate-800 rounded-sm relative p-2 grid grid-cols-5 grid-rows-3 gap-1 shadow-inner opacity-80">
            {Array.from({ length: 13 }).map((_, i) => (
              <div key={i} className="bg-ms-glass/30 border border-ms-glass/50 rounded-[1px]"></div>
            ))}
            <div className="bg-red-900/20 col-span-2 row-start-3 rounded-[1px] flex items-center justify-center border border-red-900/50">
              <span className="text-[8px] text-red-500 font-mono font-bold">SCRAP</span>
            </div>
          </div>
        </div>
      </div>

      {isWasteViolation ? (
        <div className="mt-8 p-4 bg-red-500/5 border border-red-500/20 rounded-sm flex items-start gap-4 animate-pulse">
          <AlertTriangle className="text-red-500 shrink-0" size={20} />
          <p className="text-[10px] font-bold text-red-500/80 uppercase tracking-tight leading-relaxed italic">
            // Waste Violation Detected: Scrap exceeds Madinat Al Saada 5% threshold. <br/>
            // Action required: Re-evaluate stock bar length or panel orientation.
          </p>
        </div>
      ) : (
        <div className="mt-8 p-4 bg-ms-emerald/5 border border-ms-emerald/20 rounded-sm flex items-center gap-4">
          <CheckCircle2 className="text-ms-emerald" size={20} />
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            Nesting Efficiency Verified for Factory Release.
          </p>
        </div>
      )}
    </div>
  );
};

export default OptimizationVisuals;
