import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import InteractiveBOQ from '../../components/InteractiveBOQ';
import VarianceAlerts from '../../components/VarianceAlerts';
import QuantificationAuditor from '../../components/QuantificationAuditor';
import StructuralInsight from '../../components/StructuralInsight';
import { useEstimateStore } from '../../store/useEstimateStore';

const EstimatePage = () => {
  const router = useRouter();
  const { id } = router.query;
  const { boq, variances, status, setBOQ } = useEstimateStore();
  const [progress, setProgress] = useState(0);
  const [view, setView] = useState<'COMMERCIAL' | 'ENGINEERING'>('COMMERCIAL');

  useEffect(() => {
    if (!id) return;
    const timer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(timer);
          setBOQ({
            total_price_aed: 1250450.00,
            client_summary: { lme_reference_usd_mt: 2485.50 },
            line_items: [
              { desc: "Thermal Break Curtain Wall (GULF-EXT-7001)", quantity: 2450.5, amount: 850000.00 },
              { desc: "12mm Laminated Heat Soaked Glass (Double Glazed)", quantity: 1850.2, amount: 320000.00 },
              { desc: "Heavy Duty Automatic Sliding Entrance Doors", quantity: 4, amount: 45000.00 },
              { desc: "Site Installation & Logistics (Ajman)", quantity: 1, amount: 35450.00 }
            ],
            audit: {
              openings: 845,
              linear_meters: 12450.5,
              glass_sqm: 1850.2,
              miter_cuts: 4850,
              wind_pressure: 1.85,
              span: 3800,
              ixx_req: 112.5,
              ixx_prov: 95.8
            },
            variances: [
              "SAFETY_OVERRIDE: Structural failure detected on North Elevation Mullions (Span 3800mm). Required Ixx 112.5cm4 > Provided 95.8cm4. AI upgraded to GULF-EXT-7002-HD.",
              "RFI_WARNING: Discrepancy detected between Architectural Window Schedule (Sheet A-102) and BOQ Quantity for Type W-04."
            ]
          });
          return 100;
        }
        return prev + 10;
      });
    }, 300);
    return () => clearInterval(timer);
  }, [id, setBOQ]);

  return (
    <div className="min-h-screen bg-black text-slate-200 flex flex-col font-sans">
      <header className="h-16 border-b border-slate-900 flex items-center justify-between px-8 bg-slate-950">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 bg-emerald-500 rounded-sm flex items-center justify-center font-black text-black text-xs">M</div>
          <h1 className="font-bold text-xs tracking-widest uppercase">Masaad Estimator <span className="text-slate-700 ml-2">PROD_v1.0</span></h1>
        </div>
        <div className="flex bg-slate-900 p-1 rounded">
          <button 
            onClick={() => setView('COMMERCIAL')}
            className={`px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded transition-all ${view === 'COMMERCIAL' ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'}`}
          >
            Commercial_View
          </button>
          <button 
            onClick={() => setView('ENGINEERING')}
            className={`px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded transition-all ${view === 'ENGINEERING' ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'}`}
          >
            Engineering_View
          </button>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden relative">
        <div className="flex-1 p-10 overflow-y-auto">
          {status !== 'COMPLETE' ? (
            <div className="max-w-xl mx-auto space-y-6 pt-32">
              <div className="h-[1px] bg-slate-900 w-full"><div className="h-full bg-emerald-500 transition-all duration-700" style={{ width: `${progress}%` }}></div></div>
              <p className="text-center text-slate-600 text-[9px] font-mono animate-pulse uppercase tracking-widest">Running_Neuro_Symbolic_Quantification...</p>
            </div>
          ) : (
            <div className="max-w-6xl mx-auto pb-20">
              <div className="mb-10">
                <h2 className="text-4xl font-black uppercase tracking-tighter italic">{view === 'COMMERCIAL' ? 'Project_Financials' : 'Engineering_Audit'}</h2>
                <p className="text-slate-600 text-[9px] font-mono mt-2 uppercase tracking-widest">AL_KABIR_TOWER_VERIFICATION | AJMAN_UAE</p>
              </div>

              {view === 'COMMERCIAL' ? <InteractiveBOQ /> : (
                <div className="animate-in fade-in duration-500">
                  <QuantificationAuditor data={boq.audit} />
                  <StructuralInsight audit={boq.audit} />
                </div>
              )}
            </div>
          )}
        </div>
        <VarianceAlerts variances={boq?.variances || []} />

        {/* Masaad Watermark */}
        <footer className="absolute bottom-6 left-10 pointer-events-none opacity-20">
            <div className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">
                Madinat Al Saada Aluminium & Glass Works LLC
            </div>
        </footer>
      </main>
    </div>
  );
};

export default EstimatePage;