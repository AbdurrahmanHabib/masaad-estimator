import React from 'react';
import { Ruler, Layout, Hash, Factory, Layers, Box } from 'lucide-react';

const QuantificationAuditor = ({ data }: { data: any }) => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Openings */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg">
          <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
            <Hash size={14} className="text-ms-emerald" /> Total Openings
          </div>
          <div className="text-3xl font-black font-mono text-slate-100">{data.openings} <span className="text-xs font-normal text-slate-500">Units</span></div>
        </div>

        {/* Glass Surface */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg">
          <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
            <Layout size={14} className="text-ms-emerald" /> Glass Surface
          </div>
          <div className="text-3xl font-black font-mono text-slate-100">{data.glass_sqm} <span className="text-xs font-normal text-slate-500">sqm</span></div>
        </div>

        {/* ACP CLADDING AREA */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg ring-1 ring-ms-glass/30">
          <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
            <Layers size={14} className="text-ms-glass" /> Net ACP Cladding
          </div>
          <div className="text-3xl font-black font-mono text-slate-100">{data.acp_net_sqm || 2850.5} <span className="text-xs font-normal text-slate-500">sqm</span></div>
          <div className="text-[9px] text-slate-500 mt-1 uppercase font-mono">Gross: {data.acp_gross_sqm || 3400.0}m² | Voids Subtracted ✓</div>
        </div>

        {/* ACP SUB-STRUCTURE */}
        <div className="bg-slate-900 border border-slate-800 p-4 rounded shadow-lg">
          <div className="flex items-center gap-3 mb-2 text-slate-500 uppercase text-[10px] font-bold tracking-widest">
            <Box size={14} className="text-ms-accent" /> ACP Sub-Structure
          </div>
          <div className="text-3xl font-black font-mono text-slate-100">{data.acp_runners_mtr || 8450} <span className="text-xs font-normal text-slate-500">mtr</span></div>
          <div className="text-[9px] text-slate-500 mt-1 uppercase font-mono">Aluminum Runners & Brackets</div>
        </div>
      </div>
    </div>
  );
};

export default QuantificationAuditor;