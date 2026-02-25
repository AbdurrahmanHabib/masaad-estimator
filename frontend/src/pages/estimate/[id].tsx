import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import InteractiveBOQ from '../../components/InteractiveBOQ';
import VarianceAlerts from '../../components/VarianceAlerts';
import QuantificationAuditor from '../../components/QuantificationAuditor';
import StructuralInsight from '../../components/StructuralInsight';
import ExportCenter from '../../components/ExportCenter';
import { useEstimateStore } from '../../store/useEstimateStore';

const EstimatePage = () => {
  const router = useRouter();
  const { id } = router.query;
  const { boq, status, setBOQ } = useEstimateStore();
  const [progress, setProgress] = useState(0);
  const [view, setView] = useState<'COMMERCIAL' | 'ENGINEERING'>('COMMERCIAL');

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
            total_price_aed: 1845600.00, // Price increased due to ACP
            client_summary: { lme_reference_usd_mt: 2485.50 },
            line_items: [
              { desc: "Thermal Break Curtain Wall (GULF-EXT-7001)", quantity: 2450.5, amount: 850000.00 },
              { desc: "12mm Laminated Heat Soaked Glass (Double Glazed)", quantity: 1850.2, amount: 320000.00 },
              { desc: "ACP Cladding - 4mm PVDF Coating (Alucopanel/Alubond)", quantity: 2850.5, amount: 545000.00 },
              { desc: "ACP Secondary Sub-structure (Alum Runners/Brkts)", quantity: 8450, amount: 95150.00 },
              { desc: "Site Installation & Logistics (Ajman)", quantity: 1, amount: 35450.00 }
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
            variances: [
              "SAFETY_OVERRIDE: Structural failure detected on North Elevation Mullions. AI upgraded to GULF-EXT-7002-HD.",
              "ACP_CALCULATION: Detected 549.5 m² of window/door voids subtracted from gross ACP area across all side-by-side layouts.",
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

  return (
    <div className="min-h-screen bg-ms-bg flex flex-col font-sans selection:bg-ms-glass/20">
      <header className="h-20 bg-white/90 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-10 z-50">
        <div className="flex items-center gap-5">
          <img src="/logo.png" alt="Logo" className="h-8 w-auto object-contain" />
          <div className="h-6 w-[1px] bg-slate-200"></div>
          <div className="flex flex-col">
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-ms-primary">Al Kabir Tower</span>
            <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Kabul, AF // ACP & Glazing Audit</span>
          </div>
        </div>
        
        <div className="flex bg-slate-100 p-1 rounded-sm">
          <button onClick={() => setView('COMMERCIAL')} className={`px-6 py-2 text-[9px] font-black uppercase tracking-widest rounded-sm transition-all ${view === 'COMMERCIAL' ? 'bg-ms-primary text-white shadow-lg shadow-ms-primary/20' : 'text-slate-400'}`}>Commercial</button>
          <button onClick={() => setView('ENGINEERING')} className={`px-6 py-2 text-[9px] font-black uppercase tracking-widest rounded-sm transition-all ${view === 'ENGINEERING' ? 'bg-ms-primary text-white shadow-lg shadow-ms-primary/20' : 'text-slate-400'}`}>Engineering</button>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden relative">
        <div className="flex-1 p-12 overflow-y-auto">
          {status !== 'COMPLETE' ? (
            <div className="max-w-xl mx-auto pt-40 space-y-6">
              <div className="h-[2px] bg-slate-100 w-full"><div className="h-full bg-ms-glass transition-all duration-500" style={{ width: `${progress}%` }}></div></div>
              <p className="text-center text-slate-400 text-[9px] font-mono animate-pulse uppercase tracking-[0.3em]">Processing_Layouts_&_ACP_Matrix...</p>
            </div>
          ) : (
            <div className="max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
              {view === 'COMMERCIAL' ? <InteractiveBOQ /> : (
                <>
                  <QuantificationAuditor data={boq.audit} />
                  <StructuralInsight audit={boq.audit} />
                </>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-col border-l border-slate-100 h-full">
            <VarianceAlerts variances={boq?.variances || []} />
            <ExportCenter project_id={id as string} />
        </div>

        <div className="absolute bottom-8 left-12 text-[8px] font-mono text-slate-300 uppercase tracking-[0.2em] pointer-events-none">
          Architecture by Masaad // Madinat Al Saada Corp.
        </div>
      </main>
    </div>
  );
};

export default EstimatePage;