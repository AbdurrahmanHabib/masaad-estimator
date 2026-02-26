import React, { useState } from 'react';
import { Building2, ToggleRight, ShieldCheck, PieChart } from 'lucide-react';

const GroupConsolidation = ({ stats }: { stats: any }) => {
  const [consolidated, setConsolidated] = useState(true);

  return (
    <div className="bg-white border border-[#e2e8f0] p-6 shadow-card rounded-xl">
      <div className="flex justify-between items-center mb-6 border-b border-[#e2e8f0] pb-4">
        <h3 className="text-sm font-bold text-[#0f172a] flex items-center gap-2">
          <Building2 size={16} className="text-[#1e3a5f]" /> Unified Group Governance
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-semibold text-[#64748b] uppercase tracking-wider">Merge Shell Entities</span>
          <button onClick={() => setConsolidated(!consolidated)} className={`${consolidated ? 'text-[#10b981]' : 'text-[#64748b]'} transition-all`}>
            <ToggleRight size={28} fill={consolidated ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {['Madinat Al Saada', 'Al Jazeera', 'Madinat Al Jazeera'].map((name, i) => (
          <div key={i} className="p-4 bg-slate-50 border border-[#e2e8f0] rounded-xl">
            <span className="text-[10px] font-semibold text-[#64748b] block mb-1">{name}</span>
            <span className="text-sm font-mono text-[#10b981] font-semibold">Linked</span>
          </div>
        ))}
      </div>

      <div className="bg-emerald-50 border border-emerald-200 p-5 rounded-xl flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
            <ShieldCheck size={20} className="text-[#10b981]" />
          </div>
          <div>
            <span className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider block">Consolidated Burdened Rate</span>
            <p className="text-2xl font-mono font-bold text-[#0f172a]">AED {consolidated ? stats?.true_shop_rate_aed || "42.50" : "0.00"}/hr</p>
          </div>
        </div>
        <div className="text-right">
          <PieChart size={20} className="text-[#64748b] ml-auto mb-1" />
          <span className="text-[10px] text-[#64748b] font-medium">Recovery: 100%</span>
        </div>
      </div>
    </div>
  );
};

export default GroupConsolidation;
