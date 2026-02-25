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
  Scale,
  Briefcase,
  MapPin,
  Clock,
  CheckCircle2
} from 'lucide-react';

const EstimatePage = () => {
  const router = useRouter();
  const { id } = router.query;
  const { boq, status, setBOQ } = useEstimateStore();
  const [progress, setProgress] = useState(0);
  const [workbench, setWorkbench] = useState<'BOQ' | 'OPTIMIZATION' | 'STRUCTURAL'>('BOQ');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
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

  if (!mounted) return <div className="min-h-screen bg-ms-bg" />;

  if (status !== 'COMPLETE' || !boq) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-ms-bg p-20">
        <div className="w-full max-w-md space-y-6 bg-white p-10 rounded-2xl shadow-xl border border-ms-border">
          <div className="flex justify-between items-end mb-2">
             <div className="flex flex-col">
                <span className="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em]">Fusion_Engine_Active</span>
                <h3 className="text-sm font-bold text-slate-800">Quantifying Al Kabir Tower...</h3>
             </div>
             <span className="text-xl font-mono font-black text-blue-600">{progress}%</span>
          </div>
          <div className="h-3 bg-slate-100 w-full rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-500 to-blue-700 transition-all duration-500 shadow-lg" style={{ width: `${progress}%` }}></div>
          </div>
          <div className="flex items-center gap-2 text-slate-400">
             <Clock size={14} className="animate-spin" />
             <p className="text-[10px] font-medium uppercase tracking-widest">Extracting Geometry & Specs...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-ms-bg overflow-hidden gap-6">
      {/* TOP PROJECT BAR */}
      <div className="flex items-center justify-between bg-white p-6 rounded-2xl shadow-sm border border-ms-border">
        <div className="flex items-center gap-6">
          <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center text-blue-600 shadow-inner">
            <Briefcase size={28} />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-xl font-black text-slate-800 uppercase tracking-tighter">{boq.name}</h1>
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-600 text-[9px] font-black uppercase tracking-widest rounded-md border border-emerald-200">Active_Audit</span>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500 font-medium">
              <span className="flex items-center gap-1.5"><MapPin size={14} /> {boq.location}</span>
              <span className="w-1 h-1 bg-slate-300 rounded-full"></span>
              <span className="flex items-center gap-1.5"><Clock size={14} /> Last Update: Today, 4:15 PM</span>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="px-6 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all shadow-lg">History</button>
          <button className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all shadow-lg shadow-blue-600/20">Release Project</button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden gap-6">
        
        {/* PANE 1: DWG LAYERS (20%) */}
        <div className="w-[20%] flex flex-col bg-white rounded-2xl shadow-sm border border-ms-border overflow-hidden">
          <div className="p-4 border-b border-ms-border flex items-center gap-2 bg-slate-50/50">
            <Layers size={18} className="text-blue-600" />
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-800">Layer Control</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {boq.layers?.map((layer: string) => (
              <div key={layer} className="flex items-center justify-between p-3 bg-slate-50 border border-slate-100 rounded-xl hover:border-blue-300 hover:bg-blue-50/30 transition-all cursor-pointer group">
                <span className="text-[10px] font-bold text-slate-600 group-hover:text-blue-700 transition-colors uppercase">{layer}</span>
                <div className="w-2 h-2 bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]"></div>
              </div>
            ))}
          </div>
          <div className="p-4 border-t border-ms-border bg-slate-50/50">
            <div className="flex items-center gap-2 mb-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
              <Cpu size={14} className="text-blue-600" /> System Logic Status
            </div>
            <div className="flex items-center justify-between mb-1 text-[9px] font-bold text-slate-400">
               <span>CORE_V2.5</span>
               <span className="text-emerald-600">OPTIMIZED</span>
            </div>
            <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 w-full"></div>
            </div>
          </div>
        </div>

        {/* PANE 2: ACTIVE WORKBENCH (50%) */}
        <div className="w-[50%] flex flex-col bg-white rounded-2xl shadow-sm border border-ms-border overflow-hidden relative">
          {/* WORKBENCH TOGGLE */}
          <div className="p-4 border-b border-ms-border flex justify-between items-center bg-slate-50/50 backdrop-blur-sm sticky top-0 z-10">
            <div className="flex gap-2 p-1 bg-slate-100 rounded-xl border border-slate-200">
              <button 
                onClick={() => setWorkbench('BOQ')} 
                className={`px-4 py-2 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all flex items-center gap-2 ${workbench === 'BOQ' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <BarChart3 size={14} /> BOQ Grid
              </button>
              <button 
                onClick={() => setWorkbench('OPTIMIZATION')} 
                className={`px-4 py-2 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all flex items-center gap-2 ${workbench === 'OPTIMIZATION' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <Box size={14} /> Nesting 2D
              </button>
              <button 
                onClick={() => setWorkbench('STRUCTURAL')} 
                className={`px-4 py-2 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all flex items-center gap-2 ${workbench === 'STRUCTURAL' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <HardHat size={14} /> Structural
              </button>
            </div>
            <div className="flex flex-col items-end">
               <span className="text-[8px] font-black text-slate-400 uppercase tracking-[0.2em]">Workbench_State</span>
               <span className="text-[10px] font-mono font-bold text-blue-600 tracking-tighter uppercase">{workbench}_ACTIVE</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {workbench === 'BOQ' && (
              <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                <InteractiveBOQ />
              </div>
            )}
            {workbench === 'OPTIMIZATION' && (
              <div className="animate-in fade-in slide-in-from-bottom-2 duration-500 h-full">
                <OptimizationVisualizer />
              </div>
            )}
            {workbench === 'STRUCTURAL' && (
              <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                <StructuralChecklist />
              </div>
            )}
          </div>
        </div>

        {/* PANE 3: FINANCIAL PULSE SIDEBAR (30%) */}
        <div className="w-[30%] flex flex-col gap-6 overflow-hidden">
          
          {/* PRIMARY METRICS */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-ms-border space-y-6">
            <div className="flex items-center justify-between border-b border-ms-border pb-4">
               <div className="flex items-center gap-2">
                  <TrendingUp size={18} className="text-blue-600" />
                  <h3 className="text-xs font-bold uppercase tracking-widest text-slate-800">Commercial Pulse</h3>
               </div>
               <span className="text-[9px] font-bold text-slate-400 uppercase">Live_Sync</span>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <div className="p-5 bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-2xl shadow-lg shadow-emerald-500/20 text-white group hover:scale-[1.02] transition-all">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-[10px] font-bold uppercase tracking-widest opacity-80 italic">True Burdened Rate</span>
                  <div className="p-2 bg-white/20 rounded-lg"><Activity size={16} /></div>
                </div>
                <div className="text-3xl font-mono font-black tabular-nums tracking-tighter">
                  AED {(boq.true_shop_rate || 48.75).toFixed(2)}
                </div>
                <div className="mt-4 flex items-center gap-2 text-[9px] font-bold uppercase tracking-widest bg-white/10 w-fit px-2 py-1 rounded-md">
                   <CheckCircle2 size={10} /> Factory_Pool_Verified
                </div>
              </div>

              <div className="p-5 bg-gradient-to-br from-blue-600 to-blue-800 rounded-2xl shadow-lg shadow-blue-600/20 text-white group hover:scale-[1.02] transition-all">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-[10px] font-bold uppercase tracking-widest opacity-80 italic">Total Project Value</span>
                  <div className="p-2 bg-white/20 rounded-lg"><DollarSign size={16} /></div>
                </div>
                <div className="text-3xl font-mono font-black tabular-nums tracking-tighter">
                  AED {boq.total_price_aed?.toLocaleString() || '0.00'}
                </div>
                <p className="text-[9px] font-medium mt-4 opacity-70 uppercase tracking-widest">Market Reference: Dec 2025</p>
              </div>
            </div>
          </div>

          {/* ALERTS & EXPORT */}
          <div className="flex-1 overflow-y-auto space-y-6">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-ms-border">
              <div className="flex items-center gap-2 mb-4 text-[10px] font-bold text-amber-600 uppercase tracking-widest italic underline decoration-amber-200 decoration-2 underline-offset-4">
                <ShieldAlert size={16} /> Technical Deviations
              </div>
              <VarianceAlerts variances={boq?.variances || []} />
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-ms-border">
              <ExportCenter project_id={id as string} />
            </div>
          </div>
        </div>
      </div>

      {/* STICKY PROJECT FOOTER */}
      <div className="bg-slate-800 p-6 rounded-2xl shadow-2xl flex items-center justify-between text-white border border-slate-700">
        <div className="flex items-center gap-12 flex-1">
          <div className="flex flex-col">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Final Sell Price</span>
            <span className="text-2xl font-mono font-black text-emerald-400 tabular-nums tracking-tighter">
              AED {boq.total_price_aed?.toLocaleString() || '0.00'}
            </span>
          </div>
          
          <div className="h-10 w-[1px] bg-slate-700"></div>

          <div className="flex flex-col">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Net Material Mass</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-mono font-black text-white tabular-nums tracking-tighter">
                {(boq.audit.linear_meters * 2.45).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
              <span className="text-xs font-bold text-slate-500">KG</span>
            </div>
          </div>

          <div className="h-10 w-[1px] bg-slate-700"></div>

          <div className="flex flex-col">
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Estimated Net Profit</span>
            <div className="flex items-center gap-4">
              <span className="text-2xl font-mono font-black text-emerald-400 tabular-nums tracking-tighter">24.8%</span>
              <div className="w-24 h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-700">
                <div className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 w-[75%] shadow-[0_0_10px_#10b981]"></div>
              </div>
            </div>
          </div>
        </div>

        <button className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-black uppercase tracking-[0.2em] transition-all shadow-lg shadow-blue-600/20 hover:scale-[1.02]">
          Commit Final Audit
        </button>
      </div>
    </div>
  );
};

export default EstimatePage;