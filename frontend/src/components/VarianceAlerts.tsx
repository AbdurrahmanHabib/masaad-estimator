import React from 'react';
import { AlertTriangle, ShieldAlert } from 'lucide-react';

const VarianceAlerts = ({ variances = [] }: { variances?: string[] }) => {
  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {variances.map((v, i) => (
          <div key={i} className={`p-4 rounded-sm border transition-all hover:shadow-[0_0_15px_rgba(245,158,11,0.1)] group ${v.includes("SAFETY") ? "bg-red-500/5 border-red-500/30 text-red-200" : "bg-ms-amber/5 border-ms-amber/30 text-amber-200"}`}>
            <div className="flex items-center gap-2 font-black mb-2 uppercase text-[9px] tracking-[0.2em]">
              {v.includes("SAFETY") ? <ShieldAlert size={12} className="text-red-500" /> : <AlertTriangle size={12} className="text-ms-amber" />}
              {v.includes("SAFETY") ? "Critical_Security_Override" : "Logic_Variance_Detected"}
            </div>
            <p className="text-[10px] leading-relaxed font-mono text-slate-400 group-hover:text-slate-300 transition-colors">
              {v}
            </p>
          </div>
        ))}
        {variances.length === 0 && (
          <div className="bg-ms-panel border border-ms-border p-6 text-center rounded-sm">
            <p className="text-slate-600 text-[9px] font-mono uppercase tracking-[0.3em]">No_Deviations_Flagged</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default VarianceAlerts;