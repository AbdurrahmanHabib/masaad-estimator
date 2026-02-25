import React, { useState } from 'react';
import { Building2, ToggleRight, ShieldCheck, PieChart } from 'lucide-react';

const GroupConsolidation = ({ stats }: { stats: any }) => {
  const [consolidated, setConsolidated] = useState(true);

  return (
    <div className="bg-slate-900 border border-slate-800 p-8 shadow-2xl rounded-sm">
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <h3 className="text-sm font-black uppercase tracking-widest text-white italic flex items-center gap-2">
          <Building2 size={16} className="text-ms-emerald" /> Unified_Group_Governance
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Merge Shell Entities</span>
          <button onClick={() => setConsolidated(!consolidated)} className={`${consolidated ? 'text-ms-emerald' : 'text-slate-600'} transition-all`}>
            <ToggleRight size={28} fill={consolidated ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-8">
        {['Madinat Al Saada', 'Al Jazeera', 'Madinat Al Jazeera'].map((name, i) => (
          <div key={i} className="p-4 bg-slate-950/50 border border-slate-800 rounded-sm">
            <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1 tracking-tighter">{name}</span>
            <span className="text-xl font-mono text-white opacity-40 italic">Linked ✓</span>
          </div>
        ))}
      </div>

      <div className="bg-ms-emerald/5 border border-ms-emerald/20 p-6 rounded-sm flex items-center justify-between shadow-lg shadow-emerald-500/5">
        <div className="flex items-center gap-4">
          <ShieldCheck size={24} className="text-ms-emerald" />
          <div>
            <span className="text-[10px] font-black text-ms-emerald uppercase tracking-widest block">Consolidated_Burdened_Rate</span>
            <p className="text-3xl font-mono font-black text-white">AED {consolidated ? stats?.true_shop_rate_aed || "42.50" : "0.00"}/hr</p>
          </div>
        </div>
        <div className="text-right">
            <PieChart size={24} className="text-slate-700 ml-auto mb-1" />
            <span className="text-[8px] font-mono text-slate-500 uppercase">Recovery Ratio: 100%</span>
        </div>
      </div>
    </div>
  );
};

export default GroupConsolidation;
