import React from 'react';
import { Factory, Scissors, AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react';

const ProductionPreview = ({ data }: { data: any }) => {
  if (!data) return null;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* HEADER SECTION */}
      <div className="flex justify-between items-end border-b border-slate-800 pb-6">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tighter text-white italic flex items-center gap-3">
            <Factory className="text-ms-emerald" /> Production_&_Optimization_Audit
          </h2>
          <p className="text-[10px] text-slate-500 font-mono mt-1 uppercase tracking-[0.3em]">Factory Floor Readiness Sequence</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Efficiency_Score:</span>
          <span className={`text-xl font-mono font-black ${data.scrap_pct > 8 ? 'text-red-500' : 'text-ms-emerald'}`}>
            {100 - data.scrap_pct}%
          </span>
        </div>
      </div>

      {/* OPTIMIZATION CARDS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* 1D ALUMINUM OPTIMIZER */}
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl relative group">
          <div className="absolute top-0 right-0 p-3 bg-slate-800 border-l border-b border-slate-700 text-[8px] font-black text-slate-500 uppercase tracking-widest">Sequence_01</div>
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2">
            <Scissors size={14} className="text-ms-emerald" /> 1D_Extrusion_Nesting
          </h3>
          <div className="grid grid-cols-2 gap-10">
            <div>
              <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest block mb-1">Meters_Required</span>
              <p className="text-3xl font-mono font-black text-white">{data.linear_meters}m</p>
            </div>
            <div>
              <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest block mb-1">Stock_Bars_to_Order</span>
              <p className="text-3xl font-mono font-black text-ms-emerald">{data.total_bars} <span className="text-xs">PCS</span></p>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-slate-800 flex justify-between items-center">
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Optimized using CP-SAT // 5mm Kerf</span>
            <button className="text-[10px] font-black text-ms-emerald uppercase tracking-tighter flex items-center hover:gap-2 transition-all">
              View_Cutting_List <ChevronRight size={14} />
            </button>
          </div>
        </div>

        {/* 2D ACP OPTIMIZER */}
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl relative group">
          <div className="absolute top-0 right-0 p-3 bg-slate-800 border-l border-b border-slate-700 text-[8px] font-black text-slate-500 uppercase tracking-widest">Sequence_02</div>
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2">
            <Scissors size={14} className="text-ms-glass" /> 2D_Sheet_Nesting (ACP)
          </h3>
          <div className="grid grid-cols-2 gap-10">
            <div>
              <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest block mb-1">Net_SQM_Required</span>
              <p className="text-3xl font-mono font-black text-white">{data.acp_sqm}m²</p>
            </div>
            <div>
              <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest block mb-1">Raw_Sheets_to_Order</span>
              <p className="text-3xl font-mono font-black text-ms-glass">{data.total_sheets} <span className="text-xs">PCS</span></p>
            </div>
          </div>
          <div className="mt-8 pt-6 border-t border-slate-800 flex justify-between items-center">
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">+50mm Folding_Returns_Applied</span>
            <button className="text-[10px] font-black text-ms-glass uppercase tracking-tighter flex items-center hover:gap-2 transition-all">
              View_Routing_Map <ChevronRight size={14} />
            </button>
          </div>
        </div>

      </div>

      {/* SCRAP WARNING */}
      {data.scrap_pct > 8 && (
        <div className="bg-red-500/10 border border-red-500/30 p-6 rounded-sm flex items-start gap-4 shadow-xl">
          <AlertTriangle size={24} className="text-red-500 shrink-0" />
          <div>
            <h4 className="text-[11px] font-black text-red-500 uppercase tracking-widest">Material_Waste_Violation</h4>
            <p className="text-[10px] font-mono text-red-400/70 mt-2 leading-relaxed uppercase tracking-tighter">
              Calculated scrap is <span className="font-black text-red-500">{data.scrap_pct}%</span>. This exceeds the 8.00% threshold for Madinat Al Saada. 
              <br/>Manual intervention required: Re-evaluate panel orientation or stock length.
            </p>
          </div>
        </div>
      )}

      {data.scrap_pct <= 8 && (
        <div className="bg-emerald-500/5 border border-emerald-500/10 p-6 rounded-sm flex items-start gap-4">
          <CheckCircle2 size={24} className="text-ms-emerald shrink-0 opacity-50" />
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
            Yield Efficiency within safe margins. Cutting list verified for factory release.
          </p>
        </div>
      )}

    </div>
  );
};

export default ProductionPreview;
