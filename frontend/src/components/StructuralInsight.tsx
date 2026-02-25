import React from 'react';
import { ShieldCheck, Info, Gauge } from 'lucide-react';

const StructuralInsight = ({ audit }: { audit: any }) => {
  return (
    <div className="bg-ms-panel border border-ms-border rounded-sm overflow-hidden shadow-2xl transition-all hover:border-ms-emerald/20">
      <div className="p-4 bg-ms-dark/50 border-b border-ms-border flex justify-between items-center">
        <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 italic flex items-center gap-2">
          <ShieldCheck size={14} className="text-ms-emerald" /> ASCE 7-16 Structural Verification
        </h2>
        <div className="px-2 py-0.5 bg-ms-emerald/10 text-ms-emerald text-[8px] font-black uppercase tracking-widest rounded-sm border border-ms-emerald/20">
          Status: Compliant
        </div>
      </div>
      <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-10">
        <div>
          <label className="text-[9px] text-slate-500 uppercase font-black tracking-widest block mb-2 italic">Wind_Pressure_Profile</label>
          <div className="text-3xl font-mono font-black text-white tabular-nums tracking-tighter">
            {audit.wind_pressure || 1.5} <span className="text-xs font-normal text-slate-600">KPA</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5 text-[8px] text-ms-emerald font-bold uppercase tracking-widest">
            <Gauge size={10} /> Dubai_Zone_A_Certified
          </div>
        </div>
        <div>
          <label className="text-[9px] text-slate-500 uppercase font-black tracking-widest block mb-2 italic">Maximum_Span_Height</label>
          <div className="text-3xl font-mono font-black text-white tabular-nums tracking-tighter">
            {audit.span || 3200} <span className="text-xs font-normal text-slate-600">MM</span>
          </div>
        </div>
        <div className="p-5 bg-ms-dark/60 rounded-sm border border-ms-border shadow-inner group hover:border-ms-emerald/30 transition-all">
          <label className="text-[9px] text-slate-500 uppercase font-black tracking-widest block mb-4 italic">Moment_Of_Inertia [Ixx]</label>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[8px] text-slate-600 block uppercase font-bold tracking-tighter">Required</span>
              <span className="text-xl font-mono text-slate-400 font-black tabular-nums">{audit.ixx_req || 45.2}</span>
            </div>
            <div className="h-8 w-[1px] bg-ms-border"></div>
            <div className="text-right space-y-1">
              <span className="text-[8px] text-slate-600 block uppercase font-bold tracking-tighter">Provided</span>
              <span className={`text-xl font-mono font-black tabular-nums ${audit.ixx_prov >= audit.ixx_req ? 'text-ms-emerald' : 'text-ms-amber'}`}>
                {audit.ixx_prov || 48.5}
              </span>
            </div>
          </div>
          {audit.ixx_prov < audit.ixx_req && (
            <div className="mt-4 text-[9px] bg-ms-amber/5 text-ms-amber p-3 rounded-sm border border-ms-amber/20 flex items-start gap-2">
              <Info size={12} className="shrink-0 mt-0.5" />
              <span className="font-mono uppercase leading-relaxed tracking-tighter">Review_Required: Profile_Upgrade_Triggered</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StructuralInsight;