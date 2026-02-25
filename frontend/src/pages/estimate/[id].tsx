import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import InteractiveBOQ from '../../components/InteractiveBOQ';
import VarianceAlerts from '../../components/VarianceAlerts';
import QuantificationAuditor from '../../components/QuantificationAuditor';
import ExportCenter from '../../components/ExportCenter';
import OptimizationVisualizer from '../../components/Estimator/OptimizationVisualizer';
import StructuralChecklist from '../../components/Estimator/StructuralChecklist';
import { useEstimateStore } from '../../store/useEstimateStore';
import { 
  Layers, 
  Activity, 
  DollarSign, 
  ShieldAlert, 
  Cpu, 
  BarChart3, 
  Box, 
  HardHat,
  TrendingUp,
  Scale
} from 'lucide-react';

const EstimatePage = () => {
  const router = useRouter();
  const { id } = router.query;
  const { boq, status, setBOQ } = useEstimateStore();
  const [progress, setProgress] = useState(0);
  const [workbench, setWorkbench] = useState<'BOQ' | 'OPTIMIZATION' | 'STRUCTURAL'>('BOQ');

  useEffect(() => {
    if (!id) return;
    const timer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(timer);
          setBOQ({
            id: id,
            name: "AL KABIR TOWER - PHASE 1",
            location: "Kabul, Afghanistan (Export)",
            lme_ref: 2485.50,
            true_shop_rate: 48.75,
            total_price_aed: 1845600.00,
            client_summary: { lme_reference_usd_mt: 2485.50 },
            line_items: [
              { desc: "Thermal Break Curtain Wall (GULF-EXT-7001)", quantity: 2450.5, amount: 850000.00 },
              { desc: "12mm Laminated Heat Soaked Glass (Double Glazed)", quantity: 1850.2, amount: 320000.00 },
              { desc: "ACP Cladding - 4mm PVDF Coating", quantity: 2850.5, amount: 545000.00 },
              { desc: "ACP Secondary Sub-structure", quantity: 8450, amount: 95150.00 },
              { desc: "Site Installation & Logistics", quantity: 1, amount: 35450.00 }
            ],
            audit: {
              openings: 845,
              linear_meters: 12450.5,
              glass_sqm: 1850.2,
              acp_gross_sqm: 3400.0,
              acp_net_sqm: 2850.5,
              acp_runners_mtr: 8450,
              wind_pressure: 1.85,
              span: 3800,
              ixx_req: 112.5,
              ixx_prov: 115.8
            },
            layers: ['A-CW-EXT', 'A-CW-INT', 'A-GLASS-VIS', 'A-ACP-PNL', 'A-STR-BRK'],
            variances: [
              "SAFETY_OVERRIDE: Structural failure detected on North Elevation Mullions.",
              "ACP_CALCULATION: Detected 549.5 m² of window/door voids subtracted.",
              "KABUL_PRESSURE: Pressure equalization valves added to all DGU units."
            ]
          });
          return 100;
        }
        return prev + 10;
      });
    }, 200);
    return () => clearInterval(timer);
  }, [id, setBOQ]);

  if (status !== 'COMPLETE') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-ms-dark p-20">
        <div className="w-full max-w-md space-y-4">
          <div className="flex justify-between items-end mb-2">
             <span className="text-[10px] font-black text-ms-emerald uppercase tracking-[0.2em]">Agent_Fusion_In_Progress</span>
             <span className="text-xs font-mono text-white">{progress}%</span>
          </div>
          <div className="h-1 bg-ms-border w-full rounded-full overflow-hidden">
            <div className="h-full bg-ms-emerald transition-all duration-500 shadow-[0_0_10px_#10b981]" style={{ width: `${progress}%` }}></div>
          </div>
          <p className="text-center text-slate-500 text-[8px] font-mono animate-pulse uppercase tracking-[0.4em]">Quantifying_Geometry_&_Specs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-ms-dark overflow-hidden">
      <div className="flex flex-1 overflow-hidden divide-x divide-ms-border">
        
        {/* PANE 1: DWG LAYERS (20%) */}
        <div className="w-[20%] flex flex-col bg-ms-dark overflow-hidden">
          <div className="p-3 border-b border-ms-border flex items-center gap-2 bg-ms-panel/20">
            <Layers size={14} className="text-slate-500" />
            <h3 className="text-[9px] font-black uppercase tracking-widest text-slate-300 italic">DWG_Layer_Control</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
            {boq.layers?.map((layer: string) => (
              <div key={layer} className="flex items-center justify-between p-2.5 bg-ms-panel/30 border border-ms-border rounded-sm hover:border-ms-emerald/30 transition-all cursor-pointer group">
                <span className="text-[9px] font-mono text-slate-400 group-hover:text-white transition-colors">{layer}</span>
                <Activity size={10} className="text-slate-700 group-hover:text-ms-emerald transition-colors" />
              </div>
            ))}
          </div>
          <div className="p-3 border-t border-ms-border bg-ms-panel/10">
            <div className="flex items-center gap-2 mb-2 text-[8px] font-bold text-slate-600 uppercase tracking-widest italic">
              <Cpu size={12} /> Extraction_Core
            </div>
            <div className="h-0.5 bg-ms-border rounded-full overflow-hidden">
              <div className="h-full bg-ms-emerald w-full shadow-[0_0_5px_#10b981]"></div>
            </div>
          </div>
        </div>

        {/* PANE 2: ACTIVE WORKBENCH (50%) */}
        <div className="w-[50%] flex flex-col bg-ms-dark relative overflow-hidden">
          {/* WORKBENCH TOGGLE */}
          <div className="p-3 border-b border-ms-border flex justify-between items-center bg-ms-panel/40 backdrop-blur-sm sticky top-0 z-10">
            <div className="flex gap-1.5 bg-ms-dark/80 p-1 border border-ms-border rounded-sm">
              <button 
                onClick={() => setWorkbench('BOQ')} 
                className={`px-3 py-1.5 text-[8px] font-black uppercase tracking-[0.2em] rounded-sm transition-all flex items-center gap-2 ${workbench === 'BOQ' ? 'bg-ms-emerald text-black shadow-lg shadow-ms-emerald/10' : 'text-slate-500 hover:text-slate-300'}`}
              >
                <BarChart3 size={12} /> Grid_View
              </button>
              <button 
                onClick={() => setWorkbench('OPTIMIZATION')} 
                className={`px-3 py-1.5 text-[8px] font-black uppercase tracking-[0.2em] rounded-sm transition-all flex items-center gap-2 ${workbench === 'OPTIMIZATION' ? 'bg-ms-emerald text-black shadow-lg shadow-ms-emerald/10' : 'text-slate-500 hover:text-slate-300'}`}
              >
                <Box size={12} /> Optimization
              </button>
              <button 
                onClick={() => setWorkbench('STRUCTURAL')} 
                className={`px-3 py-1.5 text-[8px] font-black uppercase tracking-[0.2em] rounded-sm transition-all flex items-center gap-2 ${workbench === 'STRUCTURAL' ? 'bg-ms-emerald text-black shadow-lg shadow-ms-emerald/10' : 'text-slate-500 hover:text-slate-300'}`}
              >
                <HardHat size={12} /> Structural
              </button>
            </div>
            <div className="text-[10px] font-mono text-ms-emerald font-black tracking-tighter italic">
              LIVE_WORKBENCH::{id}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {workbench === 'BOQ' && (
              <div className="animate-in fade-in slide-in-from-bottom-1 duration-300">
                <InteractiveBOQ />
              </div>
            )}
            {workbench === 'OPTIMIZATION' && (
              <div className="animate-in fade-in slide-in-from-bottom-1 duration-300 h-full">
                <OptimizationVisualizer />
              </div>
            )}
            {workbench === 'STRUCTURAL' && (
              <div className="animate-in fade-in slide-in-from-bottom-1 duration-300">
                <StructuralChecklist />
              </div>
            )}
          </div>
        </div>

        {/* PANE 3: FINANCIAL PULSE SIDEBAR (30%) */}
        <div className="w-[30%] flex flex-col bg-ms-panel/10 overflow-hidden">
          <div className="p-3 border-b border-ms-border flex items-center gap-2 bg-ms-panel/30">
            <TrendingUp size={14} className="text-ms-emerald" />
            <h3 className="text-[9px] font-black uppercase tracking-widest text-ms-emerald italic">Financial_Pulse_Center</h3>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            <div className="grid grid-cols-1 gap-4">
              <div className="p-4 bg-ms-dark border border-ms-border rounded-sm group hover:border-ms-emerald/50 transition-all shadow-xl">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest italic">True_Shop_Rate</span>
                  <Activity size={12} className="text-ms-emerald opacity-50" />
                </div>
                <div className="text-3xl font-mono text-ms-emerald font-black tabular-nums tracking-tighter">
                  AED {boq.true_shop_rate?.toFixed(2) || '48.75'}
                </div>
                <p className="text-[7px] text-slate-600 mt-2 uppercase font-mono">Real-time burdened labor index</p>
              </div>

              <div className="p-4 bg-ms-dark border border-ms-border rounded-sm group hover:border-ms-emerald/50 transition-all shadow-xl">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-[8px] text-slate-500 font-black uppercase tracking-widest italic">Total_Project_Value</span>
                  <DollarSign size={12} className="text-ms-emerald opacity-50" />
                </div>
                <div className="text-3xl font-mono text-white font-black tabular-nums tracking-tighter">
                  AED {boq.total_price_aed?.toLocaleString()}
                </div>
                <p className="text-[7px] text-slate-600 mt-2 uppercase font-mono italic">Market updated: {new Date().toLocaleDateString()}</p>
              </div>
            </div>

            <div className="border-t border-ms-border pt-4">
              <div className="flex items-center gap-2 mb-3 text-[8px] font-black text-ms-amber uppercase tracking-widest italic underline decoration-ms-amber/30">
                <ShieldAlert size={14} /> Logic_Variance_Reports
              </div>
              <VarianceAlerts variances={boq?.variances || []} />
            </div>

            <div className="border-t border-ms-border pt-4">
              <ExportCenter project_id={id as string} />
            </div>
          </div>
        </div>
      </div>

      {/* STICKY PROJECT FOOTER */}
      <footer className="h-12 bg-ms-panel border-t border-ms-emerald/30 flex items-center px-6 gap-10 z-20 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-ms-emerald animate-pulse opacity-30"></div>
        
        <div className="flex items-center gap-10 flex-1">
          <div className="flex flex-col">
            <span className="text-[7px] text-slate-500 uppercase font-black tracking-widest">Aggregate_Sell_Price</span>
            <span className="text-md font-mono text-ms-emerald font-black tabular-nums tracking-tighter">
              AED {boq.total_price_aed?.toLocaleString()}
            </span>
          </div>
          
          <div className="h-6 w-[1px] bg-ms-border"></div>

          <div className="flex flex-col">
            <span className="text-[7px] text-slate-500 uppercase font-black tracking-widest">Calculated_Net_Mass</span>
            <span className="text-md font-mono text-white font-black tabular-nums tracking-tighter">
              <Scale size={10} className="inline mr-1 text-slate-500" />
              {(boq.audit.linear_meters * 2.45).toLocaleString(undefined, { maximumFractionDigits: 0 })} <span className="text-[8px] text-slate-600">KG</span>
            </span>
          </div>

          <div className="h-6 w-[1px] bg-ms-border"></div>

          <div className="flex flex-col">
            <span className="text-[7px] text-slate-500 uppercase font-black tracking-widest">Net_Profit_Percentage</span>
            <div className="flex items-baseline gap-2">
              <span className="text-md font-mono text-ms-emerald font-black tabular-nums tracking-tighter">24.8%</span>
              <div className="w-10 h-1 bg-ms-dark border border-ms-border rounded-full overflow-hidden">
                <div className="h-full bg-ms-emerald w-[75%] shadow-[0_0_5px_#10b981]"></div>
              </div>
            </div>
          </div>
        </div>

        <button className="bg-ms-slate-800 hover:bg-ms-emerald hover:text-black text-ms-emerald px-5 py-1.5 rounded-sm text-[8px] font-black uppercase tracking-[0.2em] transition-all border border-ms-emerald/20 hover:border-ms-emerald">
          FINAL_TECHNICAL_RELEASE
        </button>
      </footer>
    </div>
  );
};

export default EstimatePage;