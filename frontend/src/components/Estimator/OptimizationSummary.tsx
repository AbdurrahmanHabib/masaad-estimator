import React from 'react';
import { ShieldCheck, TrendingDown, Factory, AlertTriangle } from 'lucide-react';

const OptimizationSummary = ({ data }: { data: any }) => {
  if (!data) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 p-8 shadow-2xl rounded-sm mt-10">
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <h3 className="text-sm font-black uppercase tracking-widest text-white italic flex items-center gap-2">
          <ShieldCheck size={16} className="text-ms-emerald" /> Margin_Protection_Matrix
        </h3>
        <span className="text-[10px] font-mono text-slate-500 uppercase">SaaS_Logic: Phase_05_Active</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        
        {/* Material Tonnage */}
        <div className="space-y-1">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Total Material Tonnage</span>
          <div className="text-3xl font-mono font-black text-white">{data.tonnage || 0.0} <span className="text-xs">MT</span></div>
        </div>

        {/* Burdened Labor */}
        <div className="space-y-1">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Burdened Labor Total</span>
          <div className="text-3xl font-mono font-black text-ms-emerald">AED {data.burdenedLaborTotal?.toLocaleString() || "0.00"}</div>
          <p className="text-[8px] text-slate-600 uppercase font-mono tracking-tighter italic">Inc. Admin & Office Overhead</p>
        </div>

        {/* Waste Alert */}
        <div className="space-y-1">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Material Waste %</span>
          <div className={`text-3xl font-mono font-black ${data.wastePct > 7 ? 'text-red-500' : 'text-white'}`}>
            {data.wastePct || 0.0}%
          </div>
          {data.wastePct > 7 && (
            <div className="flex items-center gap-1 text-red-500/70 text-[8px] uppercase font-bold animate-pulse">
              <AlertTriangle size={10} /> Scrap Threshold Violated
            </div>
          )}
        </div>

        {/* Optimization Savings */}
        <div className="bg-emerald-500/5 border border-emerald-500/10 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-ms-emerald mb-1">
            <TrendingDown size={14} />
            <span className="text-[9px] font-black uppercase tracking-widest tracking-tighter">Optimization Saving</span>
          </div>
          <div className="text-2xl font-mono font-black text-ms-emerald">AED {data.savings?.toLocaleString() || "0.00"}</div>
          <p className="text-[8px] text-emerald-500/40 uppercase font-mono italic mt-1">AI Nesting vs Industry Std (10%)</p>
        </div>

      </div>
    </div>
  );
};

export default OptimizationSummary;
