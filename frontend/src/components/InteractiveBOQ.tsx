import React from 'react';
import { useEstimateStore } from '../store/useEstimateStore';

const InteractiveBOQ = () => {
  const { boq, updateLineItem } = useEstimateStore();
  if (!boq) return (
    <div className="p-20 text-center bg-white rounded-2xl border border-ms-border">
      <div className="animate-pulse space-y-4">
        <div className="h-4 bg-slate-100 rounded w-3/4 mx-auto"></div>
        <div className="h-4 bg-slate-100 rounded w-1/2 mx-auto"></div>
        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.4em] pt-4">Awaiting_Agent_BOQ_Matrix...</p>
      </div>
    </div>
  );

  return (
    <div className="bg-white border border-ms-border rounded-2xl overflow-hidden shadow-sm transition-all hover:shadow-md">
      <div className="p-4 bg-slate-50/50 border-b border-ms-border flex justify-between items-center">
        <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 italic">Project_BOQ_Matrix</h2>
        <div className="text-[9px] text-slate-400 font-mono font-bold uppercase tracking-widest">
          LME_ALUM_REF: <span className="text-blue-600">${boq.client_summary?.lme_reference_usd_mt}</span>
        </div>
      </div>
      <table className="w-full text-left table-fixed">
        <thead className="bg-slate-50 text-slate-400 uppercase text-[8px] font-black tracking-widest border-b border-ms-border">
          <tr>
            <th className="px-6 py-4 w-1/2">System_Description</th>
            <th className="px-6 py-4 text-right">Qty_Unit</th>
            <th className="px-6 py-4 text-right">True_Rate_AED</th>
            <th className="px-6 py-4 text-right">Total_AED</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 font-sans text-xs">
          {boq.line_items?.map((item: any, idx: number) => (
            <tr key={idx} className="hover:bg-blue-50/30 transition-colors group">
              <td className="px-6 py-4 text-slate-600 font-semibold uppercase tracking-tight truncate">{item.desc}</td>
              <td className="px-6 py-4 text-right text-slate-400 font-mono">{item.quantity || 1}</td>
              <td className="px-6 py-4 text-right">
                <input 
                  type="number"
                  defaultValue={item.unit_rate || item.amount}
                  className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 w-24 text-right text-emerald-600 font-mono font-black focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all text-xs outline-none"
                  onChange={(e) => updateLineItem(idx, parseFloat(e.target.value))}
                />
              </td>
              <td className="px-6 py-4 text-right font-black text-slate-800 font-mono">
                {item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="p-6 bg-slate-50/30 flex justify-end items-end flex-col border-t border-ms-border">
        <div className="text-slate-400 text-[8px] font-black uppercase tracking-[0.3em] italic mb-1">Calculated_Project_Yield</div>
        <div className="text-4xl font-black text-blue-600 font-mono tracking-tighter tabular-nums drop-shadow-sm">
          {boq.total_price_aed?.toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default InteractiveBOQ;