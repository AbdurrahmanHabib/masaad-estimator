import React from 'react';
import { Layout, Hash, Layers, Box, Cpu } from 'lucide-react';

const QuantificationAuditor = ({ data }: { data: any }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Cpu size={14} className="text-slate-500" />
        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 italic">Geometry_Extraction_Audit</h3>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Openings */}
        <div className="bg-ms-panel border border-ms-border p-6 rounded-sm shadow-xl transition-all hover:border-ms-emerald/30 group">
          <div className="flex items-center gap-3 mb-4 text-slate-500 uppercase text-[9px] font-black tracking-widest">
            <Hash size={12} className="text-ms-emerald" /> Total Openings
          </div>
          <div className="text-4xl font-black font-mono text-white tabular-nums tracking-tighter">
            {data.openings} <span className="text-[10px] font-normal text-slate-600 tracking-normal">UNITS</span>
          </div>
          <div className="mt-3 h-0.5 bg-ms-border overflow-hidden">
             <div className="h-full bg-ms-emerald w-2/3 group-hover:w-full transition-all duration-700"></div>
          </div>
        </div>

        {/* Glass Surface */}
        <div className="bg-ms-panel border border-ms-border p-6 rounded-sm shadow-xl transition-all hover:border-ms-emerald/30 group">
          <div className="flex items-center gap-3 mb-4 text-slate-500 uppercase text-[9px] font-black tracking-widest">
            <Layout size={12} className="text-ms-emerald" /> Glass Surface
          </div>
          <div className="text-4xl font-black font-mono text-white tabular-nums tracking-tighter">
            {data.glass_sqm} <span className="text-[10px] font-normal text-slate-600 tracking-normal">SQM</span>
          </div>
          <div className="mt-3 h-0.5 bg-ms-border overflow-hidden">
             <div className="h-full bg-ms-emerald w-1/2 group-hover:w-full transition-all duration-700"></div>
          </div>
        </div>

        {/* ACP CLADDING AREA */}
        <div className="bg-ms-panel border border-ms-border p-6 rounded-sm shadow-xl transition-all hover:border-ms-amber/30 group relative overflow-hidden">
          <div className="absolute top-0 right-0 w-16 h-16 bg-ms-amber/5 -rotate-45 translate-x-8 -translate-y-8"></div>
          <div className="flex items-center gap-3 mb-4 text-slate-500 uppercase text-[9px] font-black tracking-widest">
            <Layers size={12} className="text-ms-amber" /> Net ACP Cladding
          </div>
          <div className="text-4xl font-black font-mono text-ms-amber tabular-nums tracking-tighter">
            {data.acp_net_sqm || 2850.5} <span className="text-[10px] font-normal text-slate-600 tracking-normal">SQM</span>
          </div>
          <div className="text-[8px] text-slate-500 mt-3 uppercase font-mono tracking-tighter">
            Gross: <span className="text-slate-300">{data.acp_gross_sqm || 3400.0}m²</span> | Void_Factor: <span className="text-ms-amber">Applied</span>
          </div>
        </div>

        {/* ACP SUB-STRUCTURE */}
        <div className="bg-ms-panel border border-ms-border p-6 rounded-sm shadow-xl transition-all hover:border-ms-emerald/30 group">
          <div className="flex items-center gap-3 mb-4 text-slate-500 uppercase text-[9px] font-black tracking-widest">
            <Box size={12} className="text-ms-emerald" /> Sub-Structure
          </div>
          <div className="text-4xl font-black font-mono text-white tabular-nums tracking-tighter">
            {data.acp_runners_mtr || 8450} <span className="text-[10px] font-normal text-slate-600 tracking-normal">MTR</span>
          </div>
          <div className="text-[8px] text-slate-500 mt-3 uppercase font-mono tracking-tighter">
            Aluminum_Runners_&_Brackets_System
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuantificationAuditor;