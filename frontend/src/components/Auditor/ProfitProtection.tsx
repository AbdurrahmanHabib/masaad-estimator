import React from 'react';
import { ShieldCheck, TrendingDown, DollarSign, Recycle } from 'lucide-react';

const ProfitProtection = ({ stats }: { stats: any }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-sm shadow-2xl mt-8">
      <div className="flex items-center gap-2 mb-6 border-b border-slate-800 pb-4">
        <ShieldCheck size={18} className="text-emerald-500" />
        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-white">Profit_Protection_Audit</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        <div className="space-y-1">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Direct_Material</span>
          <div className="text-2xl font-mono font-black text-white">AED {stats.materialCost?.toLocaleString()}</div>
        </div>

        <div className="space-y-1">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Direct_Labor_Rate</span>
          <div className="text-2xl font-mono font-black text-ms-emerald">AED {stats.laborRate}/hr</div>
          <div className="text-[8px] text-slate-600 uppercase font-mono tracking-tighter">Unified_Burden_Applied</div>
        </div>

        <div className="bg-emerald-500/5 border border-emerald-500/10 p-4 rounded-sm space-y-1">
          <div className="flex items-center gap-2 text-ms-emerald">
            <TrendingDown size={14} />
            <span className="text-[9px] font-bold uppercase tracking-widest">Optimization_Saving</span>
          </div>
          <div className="text-2xl font-mono font-black text-ms-emerald">AED {stats.savings?.toLocaleString()}</div>
          <p className="text-[8px] text-emerald-500/50 uppercase font-mono italic tracking-tighter">AI Nesting vs Manual Guess</p>
        </div>

        <div className="bg-slate-950 p-4 border border-slate-800 rounded-sm space-y-1">
          <div className="flex items-center gap-2 text-ms-glass">
            <Recycle size={14} />
            <span className="text-[9px] font-bold uppercase tracking-widest">Scrap_Resale_Credit</span>
          </div>
          <div className="text-xl font-mono font-black text-white">AED {stats.scrapCredit?.toLocaleString()}</div>
          <p className="text-[8px] text-slate-600 uppercase font-mono tracking-tighter">Est. Value of Offcuts & Remnants</p>
        </div>

      </div>
    </div>
  );
};

export default ProfitProtection;
