import React from 'react';
import { useEstimateStore } from '../store/useEstimateStore';

const InteractiveBOQ = () => {
  const { boq, updateLineItem } = useEstimateStore();
  if (!boq) return (
    <div className="p-20 text-center">
      <p className="text-[10px] text-slate-600 font-mono animate-pulse uppercase tracking-[0.4em]">Awaiting_Agent_BOQ_Output...</p>
    </div>
  );

  return (
    <div className="bg-ms-panel border border-ms-border rounded-sm overflow-hidden shadow-2xl transition-all hover:border-ms-emerald/20">
      <div className="p-4 bg-ms-dark/50 border-b border-ms-border flex justify-between items-center">
        <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 italic">Commercial BOQ Matrix</h2>
        <div className="text-[10px] text-slate-500 font-mono">
          LME_REF: <span className="text-ms-emerald font-black tracking-tighter">${boq.client_summary?.lme_reference_usd_mt}</span>
        </div>
      </div>
      <table className="w-full text-left">
        <thead className="bg-ms-dark/80 text-slate-500 uppercase text-[9px] font-black tracking-widest border-b border-ms-border">
          <tr>
            <th className="px-6 py-4">System_Description</th>
            <th className="px-6 py-4 text-right">Qty_Unit</th>
            <th className="px-6 py-4 text-right">True_Rate_AED</th>
            <th className="px-6 py-4 text-right">Line_Total_AED</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ms-border/50 font-mono text-xs">
          {boq.line_items?.map((item: any, idx: number) => (
            <tr key={idx} className="hover:bg-ms-emerald/[0.02] transition-colors group">
              <td className="px-6 py-4 text-slate-400 group-hover:text-white transition-colors uppercase tracking-tight">{item.desc}</td>
              <td className="px-6 py-4 text-right text-slate-500">{item.quantity || 1}</td>
              <td className="px-6 py-4 text-right">
                <input 
                  type="number"
                  defaultValue={item.unit_rate || item.amount}
                  className="bg-ms-dark border border-ms-border rounded-sm px-3 py-1.5 w-28 text-right text-ms-emerald font-black focus:outline-none focus:border-ms-emerald/50 focus:ring-1 focus:ring-ms-emerald/20 transition-all"
                  onChange={(e) => updateLineItem(idx, parseFloat(e.target.value))}
                />
              </td>
              <td className="px-6 py-4 text-right font-black text-slate-200">
                {item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="p-8 bg-ms-dark/40 flex justify-end items-end flex-col space-y-2 border-t border-ms-border">
        <div className="text-slate-500 text-[9px] uppercase font-black tracking-[0.3em] italic">Total Project Value [AED]</div>
        <div className="text-5xl font-black text-ms-emerald font-mono tracking-tighter shadow-ms-emerald/10 drop-shadow-2xl">
          {boq.total_price_aed?.toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default InteractiveBOQ;