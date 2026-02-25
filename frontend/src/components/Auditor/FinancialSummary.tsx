import React from 'react';
import { ShieldAlert, TrendingDown, DollarSign, BarChart3 } from 'lucide-react';

const FinancialSummary = ({ data }: { data: any }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl mt-10">
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <h3 className="text-sm font-black uppercase tracking-widest text-white italic flex items-center gap-2">
          <ShieldAlert size={16} className="text-ms-emerald" /> Consolidated_Margin_Protection
        </h3>
        <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono">
          <span>SOURCE: MADINAT_ADMIN_CONSOLIDATED</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
        
        {/* True Burdened Rate */}
        <div className="space-y-1">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">True Burdened Shop Rate</span>
          <div className="text-3xl font-mono font-black text-ms-emerald">AED {data.burdenedRate}/hr</div>
          <p className="text-[8px] text-slate-600 uppercase font-mono tracking-tighter italic">Factoring All Group Admin</p>
        </div>

        {/* Material Yield */}
        <div className="space-y-1">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Material Yield (Yield %)</span>
          <div className={`text-3xl font-mono font-black ${data.yield < 90 ? 'text-[#f59e0b]' : 'text-white'}`}>
            {data.yield}%
          </div>
          <p className="text-[8px] text-slate-600 uppercase font-mono tracking-tighter">Geometric vs Purchased Area</p>
        </div>

        {/* Optimization Gain */}
        <div className="bg-emerald-500/5 border border-emerald-500/10 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-ms-emerald mb-1">
            <TrendingDown size={14} />
            <span className="text-[9px] font-black uppercase tracking-widest">Nesting_Optimization_Gain</span>
          </div>
          <div className="text-2xl font-mono font-black text-ms-emerald">AED {data.gain?.toLocaleString()}</div>
          <p className="text-[8px] text-emerald-500/40 uppercase font-mono italic mt-1">Saved from Standard 15% Scrap</p>
        </div>

        {/* Project Profit Margin */}
        <div className="bg-slate-950 p-4 border border-slate-800 rounded-sm">
          <div className="flex items-center gap-2 text-slate-400 mb-1">
            <DollarSign size={14} />
            <span className="text-[9px] font-black uppercase tracking-widest">Project_Net_Margin</span>
          </div>
          <div className="text-2xl font-mono font-black text-white">AED {data.netMargin?.toLocaleString()}</div>
          <p className="text-[8px] text-slate-600 uppercase font-mono italic mt-1">Applied on top of burdened cost</p>
        </div>

      </div>
    </div>
  );
};

export default FinancialSummary;
