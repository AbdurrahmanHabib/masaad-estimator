import React from 'react';

const VarianceAlerts = ({ variances = [] }: { variances?: string[] }) => {
  return (
    <div className="w-80 h-full bg-slate-900 border-l border-slate-800 p-4 space-y-4">
      <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-slate-800 pb-2">
        Engineering Deviations
      </h3>
      <div className="space-y-3">
        {variances.map((v, i) => (
          <div key={i} className={`p-3 rounded border text-[11px] leading-relaxed font-mono ${v.includes("SAFETY") ? "bg-red-500/10 border-red-500/30 text-red-200" : "bg-amber-500/10 border-amber-500/30 text-amber-200"}`}>
            <div className="font-bold mb-1 uppercase text-[9px]">
              {v.includes("SAFETY") ? "CRITICAL OVERRIDE" : "RFI WARNING"}
            </div>
            {v}
          </div>
        ))}
        {variances.length === 0 && <div className="text-slate-600 text-xs italic text-center py-10 font-mono">NO_DEVIATIONS_DETECTED</div>}
      </div>
    </div>
  );
};

export default VarianceAlerts;