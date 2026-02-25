import React from 'react';
import { Scissors, Layout, AlertTriangle, TrendingDown } from 'lucide-react';

const OptimizationVisuals = ({ scrap_pct }: { scrap_pct: number }) => {
  const isHighWaste = scrap_pct > 5;

  return (
    <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl mt-10">
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white italic flex items-center gap-2">
          <TrendingDown size={16} className="text-ms-emerald" /> Nesting_&_Scrap_Analytics
        </h3>
        <span className="text-[10px] font-mono text-slate-500 uppercase">Engine: OR-Tools_v9.8</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
        {/* 1D ALUM VISUAL */}
        <div className="space-y-4">
          <div className="flex justify-between text-[9px] font-bold text-slate-500 uppercase tracking-widest">
            <span>Linear_Aluminum_Nesting</span>
            <span className="text-white">Efficiency: {100 - scrap_pct}%</span>
          </div>
          <div className="h-6 bg-slate-950 border border-slate-800 rounded-sm flex overflow-hidden">
            <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '40%' }}></div>
            <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '35%' }}></div>
            <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '20%' }}></div>
            <div className="h-full bg-red-900/50 flex-1"></div>
          </div>
        </div>

        {/* 2D ACP VISUAL */}
        <div className="space-y-4">
          <div className="flex justify-between text-[9px] font-bold text-slate-500 uppercase tracking-widest">
            <span>ACP_Sheet_Nesting</span>
            <span className="text-white">50mm_Returns_Applied ✓</span>
          </div>
          <div className="aspect-video bg-slate-950 border border-slate-800 rounded-sm relative p-2 grid grid-cols-4 grid-rows-3 gap-1">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="bg-ms-glass/30 border border-ms-glass/50 rounded-[1px]"></div>
            ))}
            <div className="bg-red-900/20 col-span-2 row-start-3 rounded-[1px] flex items-center justify-center">
              <span className="text-[8px] text-red-500 font-mono font-bold tracking-tighter">SCRAP_ZONE</span>
            </div>
          </div>
        </div>
      </div>

      <div className={`mt-8 p-4 rounded-sm border flex items-center justify-between ${isHighWaste ? 'bg-red-500/5 border-red-500/20' : 'bg-ms-emerald/5 border-ms-emerald/20'}`}>
        <div className="flex items-center gap-4">
          {isHighWaste ? <AlertTriangle className="text-red-500" /> : <Scissors className="text-ms-emerald" />}
          <div>
            <span className="text-[10px] font-black uppercase tracking-widest block text-slate-400">Project_Scrap_Report</span>
            <p className={`text-2xl font-mono font-black ${isHighWaste ? 'text-red-500' : 'text-white'}`}>{scrap_pct}%</p>
          </div>
        </div>
        {isHighWaste && (
          <div className="text-right text-[10px] font-bold text-red-500/70 uppercase max-w-[200px] leading-tight tracking-tighter">
            Warning: Scrap exceeds Madinat Al Saada 5% threshold. Re-nesting recommended.
          </div>
        )}
      </div>
    </div>
  );
};

export default OptimizationVisuals;
