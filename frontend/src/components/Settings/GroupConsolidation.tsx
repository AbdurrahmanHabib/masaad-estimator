import React, { useState } from 'react';
import { ShieldCheck, ToggleRight, Info, Building2 } from 'lucide-react';

const GroupConsolidation = ({ data }: { data: any }) => {
  const [isConsolidated, setIsConsolidated] = useState(true);

  return (
    <div className="bg-slate-900 border border-slate-800 p-8 shadow-2xl rounded-sm">
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <h3 className="text-sm font-black uppercase tracking-widest text-white italic flex items-center gap-2">
          <Building2 size={16} className="text-ms-emerald" /> Unified_Group_Consolidation
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Global_Auto_Merge</span>
          <button onClick={() => setIsConsolidated(!isConsolidated)} className={`${isConsolidated ? 'text-ms-emerald' : 'text-slate-600'} transition-colors`}>
            <ToggleRight size={28} fill={isConsolidated ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-sm">
          <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1 tracking-tighter">M_Al_Saada</span>
          <span className="text-xl font-mono text-white">AED {data?.entity_breakdown?.MADINAT?.toLocaleString() || "0"}</span>
        </div>
        <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-sm">
          <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1 tracking-tighter">Al_Jazeera</span>
          <span className="text-xl font-mono text-white">AED {data?.entity_breakdown?.AL_JAZEERA?.toLocaleString() || "0"}</span>
        </div>
        <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-sm">
          <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1 tracking-tighter">M_Al_Jazeera</span>
          <span className="text-xl font-mono text-white">AED {data?.entity_breakdown?.MAJ?.toLocaleString() || "0"}</span>
        </div>
      </div>

      <div className="bg-ms-emerald/5 border border-ms-emerald/20 p-6 rounded-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <ShieldCheck size={24} className="text-ms-emerald" />
          <div>
            <span className="text-[10px] font-black text-ms-emerald uppercase tracking-widest block">Group_Burdened_Rate</span>
            <p className="text-3xl font-mono font-black text-white">AED {isConsolidated ? data?.true_shop_rate_aed || "42.50" : "0.00"}/hr</p>
          </div>
        </div>
        <div className="text-right text-[9px] font-mono text-slate-500 max-w-[200px] leading-relaxed italic">
          // All shell entity expenses absorbed into Madinat Al Saada operational load.
        </div>
      </div>
    </div>
  );
};

export default GroupConsolidation;
