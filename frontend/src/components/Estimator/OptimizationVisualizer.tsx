import React from 'react';

const OptimizationVisualizer = () => {
  return (
    <div className="bg-ms-panel border border-ms-border rounded-sm overflow-hidden flex flex-col h-full">
      <div className="p-3 bg-ms-dark border-b border-ms-border flex justify-between items-center">
        <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest italic">ACP_Sheet_Optimization_2D</h3>
        <div className="flex gap-4 text-[8px] font-mono text-slate-500">
          <span>Sheet_Size: 1220x2440mm</span>
          <span className="text-ms-amber">Fold_Allowance: 50mm</span>
        </div>
      </div>
      
      <div className="flex-1 bg-ms-dark p-8 flex items-center justify-center overflow-auto">
        {/* MOCK CANVAS REPRESENTATION */}
        <div className="relative w-[400px] h-[200px] border border-ms-border bg-slate-800/20 shadow-2xl">
          <div className="absolute top-0 left-0 w-full h-full opacity-10 pointer-events-none" 
               style={{ backgroundImage: 'radial-gradient(#1e293b 1px, transparent 1px)', backgroundSize: '10px 10px' }}></div>
          
          {/* ACP PANEL 1 */}
          <div className="absolute top-[10px] left-[10px] w-[120px] h-[80px] bg-ms-emerald/10 border border-ms-emerald/40 group cursor-help transition-all hover:bg-ms-emerald/20">
             <div className="absolute inset-0 border border-dashed border-ms-emerald/20 m-[5px]"></div>
             <span className="absolute bottom-1 right-1 text-[6px] font-mono text-ms-emerald opacity-50 uppercase">Panel_A1</span>
          </div>

          {/* ACP PANEL 2 */}
          <div className="absolute top-[10px] left-[140px] w-[180px] h-[150px] bg-ms-emerald/10 border border-ms-emerald/40 group cursor-help transition-all hover:bg-ms-emerald/20">
             <div className="absolute inset-0 border border-dashed border-ms-emerald/20 m-[5px]"></div>
             <span className="absolute bottom-1 right-1 text-[6px] font-mono text-ms-emerald opacity-50 uppercase">Panel_B2</span>
          </div>

          {/* OFF-CUT / WASTE AREA */}
          <div className="absolute top-[170px] left-[10px] w-[380px] h-[20px] bg-red-500/5 border border-red-500/20 flex items-center justify-center">
             <span className="text-[6px] font-mono text-red-500/40 uppercase tracking-widest">System_Scrap_Region</span>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-ms-border grid grid-cols-3 gap-4 bg-ms-dark/50">
        <div className="space-y-1">
          <span className="text-[7px] text-slate-500 uppercase font-black tracking-tighter">Utilization_Efficiency</span>
          <div className="text-sm font-mono text-ms-emerald font-black">94.2%</div>
        </div>
        <div className="space-y-1 border-x border-ms-border px-4">
          <span className="text-[7px] text-slate-500 uppercase font-black tracking-tighter">Gross_Weight</span>
          <div className="text-sm font-mono text-white font-black">4,250 KG</div>
        </div>
        <div className="space-y-1 text-right">
          <span className="text-[7px] text-slate-500 uppercase font-black tracking-tighter">Net_Weight</span>
          <div className="text-sm font-mono text-white font-black">3,815 KG</div>
        </div>
      </div>
    </div>
  );
};

export default OptimizationVisualizer;