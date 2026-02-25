import React from 'react';
import { Ruler, Layout, Hash, Factory } from 'lucide-react';

const QuantificationAuditor = ({ data }: { data: any }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg">
        <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
          <Hash size={14} className="text-emerald-500" /> Total Openings
        </div>
        <div className="text-3xl font-black font-mono text-slate-100">{data.openings || 112} <span className="text-xs font-normal text-slate-500">Units</span></div>
      </div>
      <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg">
        <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
          <Ruler size={14} className="text-emerald-500" /> Extrusion Length
        </div>
        <div className="text-3xl font-black font-mono text-slate-100">{data.linear_meters || 1450.5} <span className="text-xs font-normal text-slate-500">mtr</span></div>
      </div>
      <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg">
        <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
          <Layout size={14} className="text-emerald-500" /> Glass Surface
        </div>
        <div className="text-3xl font-black font-mono text-slate-100">{data.glass_sqm || 420.2} <span className="text-xs font-normal text-slate-500">sqm</span></div>
      </div>
      <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg">
        <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
          <Factory size={14} className="text-emerald-500" /> Fabrication Load
        </div>
        <div className="text-3xl font-black font-mono text-slate-100">{data.miter_cuts || 450} <span className="text-xs font-normal text-slate-500">Cuts</span></div>
      </div>
    </div>
  );
};

export default QuantificationAuditor;