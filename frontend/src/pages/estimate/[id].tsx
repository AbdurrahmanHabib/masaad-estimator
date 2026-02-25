import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import InteractiveBOQ from '../../components/InteractiveBOQ';
import VarianceAlerts from '../../components/VarianceAlerts';
import { useEstimateStore } from '../../store/useEstimateStore';

const EstimatePage = () => {
  const router = useRouter();
  const { id } = router.query;
  const { boq, variances, status, setBOQ } = useEstimateStore();
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!id) return;
    // Mocking WebSocket behavior for visualization
    const timer = setInterval(() => {
        setProgress(prev => {
            if (prev >= 100) {
                clearInterval(timer);
                setBOQ({
                    total_price_aed: 45000,
                    client_summary: { lme_reference_usd_mt: 2450 },
                    line_items: [
                        { desc: "Aluminum Profiles (System 7001)", quantity: 120, amount: 15000 },
                        { desc: "12mm Laminated Glass", quantity: 45, amount: 22000 },
                        { desc: "Labor & Installation", quantity: 1, amount: 8000 }
                    ]
                });
                return 100;
            }
            return prev + 10;
        });
    }, 500);
    return () => clearInterval(timer);
  }, [id, setBOQ]);

  return (
    <div className="min-h-screen bg-black text-slate-200 flex flex-col font-sans selection:bg-emerald-500/30">
      <header className="h-16 border-b border-slate-900 flex items-center justify-between px-8 bg-slate-950">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 bg-emerald-500 rounded-sm flex items-center justify-center font-black text-black">M</div>
          <h1 className="font-bold text-sm tracking-widest uppercase">Masaad Estimator <span className="text-slate-700 font-normal ml-2 text-[10px]">INTERNAL_USE_ONLY</span></h1>
        </div>
        <div className="flex gap-4">
          <button className="px-4 py-2 border border-slate-800 hover:border-slate-600 text-[10px] font-bold uppercase tracking-wider rounded transition-all">Export_DXF</button>
          <button className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-black text-[10px] font-bold uppercase tracking-wider rounded transition-all">Print_Commercial_BOQ</button>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden">
        <div className="flex-1 p-12 overflow-y-auto">
          {status !== 'COMPLETE' && (
            <div className="max-w-xl mx-auto space-y-6 pt-32">
              <div className="flex justify-between text-[10px] font-mono text-emerald-500 tracking-tighter">
                <span>AGENT_ORCHESTRATION_SEQUENCE</span>
                <span>{progress}%</span>
              </div>
              <div className="h-[2px] bg-slate-900 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 transition-all duration-700 ease-out" style={{ width: `${progress}%` }}></div>
              </div>
              <p className="text-center text-slate-600 text-[10px] font-mono animate-pulse">EXECUTING_INGESTION_AND_STRUCTURAL_PHYSICS_ENGINE...</p>
            </div>
          )}

          {status === 'COMPLETE' && (
            <div className="max-w-5xl mx-auto animate-in fade-in duration-1000">
              <div className="mb-8 border-b border-slate-900 pb-8">
                <h2 className="text-5xl font-black uppercase tracking-tighter italic">Estimate_Review</h2>
                <p className="text-slate-600 text-[10px] font-mono mt-2">PROJECT_REF: {id} | CALIBRATION: ACTIVE | WIND_LOAD: 1.5kPa</p>
              </div>
              <InteractiveBOQ />
            </div>
          )}
        </div>
        <VarianceAlerts variances={variances} />
      </main>
    </div>
  );
};

export default EstimatePage;