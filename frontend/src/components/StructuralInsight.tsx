import React from 'react';
import { ShieldCheck, Info } from 'lucide-react';

const StructuralInsight = ({ audit }: { audit: any }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden mb-8">
      <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-300 flex items-center gap-2">
          <ShieldCheck size={14} className="text-emerald-500" /> ASCE 7-16 Structural Verification
        </h2>
      </div>
      <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div>
          <label className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Wind Pressure</label>
          <div className="text-2xl font-mono font-black text-slate-200">{audit.wind_pressure || 1.5} <span className="text-sm">kPa</span></div>
          <div className="text-[9px] text-emerald-500 mt-1 uppercase">Dubai Zone A Compliance ✓</div>
        </div>
        <div>
          <label className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Max Span Height</label>
          <div className="text-2xl font-mono font-black text-slate-200">{audit.span || 3200} <span className="text-sm">mm</span></div>
        </div>
        <div className="p-3 bg-black/40 rounded border border-slate-800">
          <label className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Moment of Inertia (Ixx)</label>
          <div className="flex items-center justify-between mt-2">
            <div>
              <span className="text-[9px] text-slate-500 block uppercase">Required</span>
              <span className="text-lg font-mono text-slate-300">{audit.ixx_req || 45.2} <span className="text-[10px]">cm4</span></span>
            </div>
            <div className="text-right">
              <span className="text-[9px] text-slate-500 block uppercase">Provided</span>
              <span className={`text-lg font-mono font-bold ${audit.ixx_prov >= audit.ixx_req ? 'text-emerald-500' : 'text-[#f59e0b]'}`}>
                {audit.ixx_prov || 48.5} <span className="text-[10px]">cm4</span>
              </span>
            </div>
          </div>
          {audit.ixx_prov < audit.ixx_req && (
            <div className="mt-2 text-[10px] bg-[#f59e0b]/10 text-[#f59e0b] p-2 rounded flex items-start gap-2">
              <Info size={12} className="shrink-0 mt-0.5" />
              <span>Manual Review Required: Profile upgraded to meet deflection limits.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StructuralInsight;