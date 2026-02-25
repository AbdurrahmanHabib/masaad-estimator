import React from 'react';
import { Scissors, BarChart3, Download, Info } from 'lucide-react';

const OptimizerDashboard = ({ data }: { data: any }) => {
  if (!data) return null;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-sm shadow-2xl overflow-hidden mt-8">
      <div className="p-5 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <Scissors size={18} className="text-ms-emerald" />
          <h2 className="text-xs font-black uppercase tracking-[0.2em] text-white italic">Factory_Cutting_Optimization</h2>
        </div>
        <button className="flex items-center gap-2 bg-ms-emerald hover:bg-emerald-500 text-black px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all rounded-sm">
          <Download size={12} /> Export_Cutting_List.PDF
        </button>
      </div>

      <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Metric 1: Bars to Order */}
        <div className="space-y-2">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Bars to Order (6.0m)</span>
          <div className="text-4xl font-mono font-black text-white leading-none">
            {data.total_bars} <span className="text-xs text-slate-600">PCS</span>
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-2">
            Σ Req: {data.total_linear_meters_req}m
          </div>
        </div>

        {/* Metric 2: Scrap Percentage */}
        <div className="space-y-2 border-l border-slate-800 pl-8">
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Calculated Scrap</span>
          <div className={`text-4xl font-mono font-black leading-none ${data.scrap_percentage < 5 ? 'text-ms-emerald' : 'text-ms-accent'}`}>
            {data.scrap_percentage}%
          </div>
          <div className="text-[10px] text-slate-400 font-mono mt-2 flex items-center gap-1">
            <Info size={10} className="text-ms-glass" /> Target: &lt; 5.00%
          </div>
        </div>

        {/* Metric 3: Profit Protection */}
        <div className="bg-slate-950 p-4 border border-slate-800 rounded-sm">
          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-3 block">Entity_Verification</span>
          <p className="text-[10px] text-slate-500 font-mono leading-relaxed">
            <span className="text-ms-emerald font-bold uppercase tracking-tighter block mb-1">✓ Madinat Al Saada Pool</span>
            Unified Blended Rate Applied. <br/>
            Kerf Width: 5.0mm.
          </p>
        </div>
      </div>

      {/* Visual Bar Summary (Mockup) */}
      <div className="px-8 pb-8">
        <div className="text-[9px] font-bold text-slate-600 uppercase tracking-widest mb-3">Nesting_Pattern_Visualization</div>
        <div className="h-4 bg-slate-950 border border-slate-800 rounded-sm flex overflow-hidden">
          <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '40%' }}></div>
          <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '30%' }}></div>
          <div className="h-full bg-ms-emerald/40 border-r border-slate-800" style={{ width: '25%' }}></div>
          <div className="h-full bg-red-950 flex-1"></div> {/* Waste */}
        </div>
        <div className="flex justify-between mt-2 text-[8px] font-mono text-slate-700 uppercase">
          <span>0.0m</span>
          <span>NESTED_Pattern_01 (95% Efficiency)</span>
          <span>6.0m</span>
        </div>
      </div>
    </div>
  );
};

export default OptimizerDashboard;