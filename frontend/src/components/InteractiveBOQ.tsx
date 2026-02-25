import React from 'react';
import { useEstimateStore } from '../store/useEstimateStore';

const InteractiveBOQ = () => {
  const { boq, updateLineItem } = useEstimateStore();
  if (!boq) return <div className="p-8 text-slate-500 text-center">Awaiting Agent Output...</div>;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-2xl">
      <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">Commercial BOQ Matrix</h2>
        <div className="text-xs text-slate-400 font-mono">
          LME Ref: <span className="text-emerald-400 font-bold">${boq.client_summary?.lme_reference_usd_mt}</span>
        </div>
      </div>
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-950 text-slate-500 uppercase text-[10px]">
          <tr>
            <th className="px-4 py-2">Description</th>
            <th className="px-4 py-2 text-right">Qty</th>
            <th className="px-4 py-2 text-right">Unit Rate (AED)</th>
            <th className="px-4 py-2 text-right">Total (AED)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 font-mono">
          {boq.line_items?.map((item: any, idx: number) => (
            <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
              <td className="px-4 py-3 text-slate-300">{item.desc}</td>
              <td className="px-4 py-3 text-right">{item.quantity || 1}</td>
              <td className="px-4 py-3 text-right">
                <input 
                  type="number"
                  defaultValue={item.unit_rate || item.amount}
                  className="bg-slate-950 border border-slate-700 rounded px-2 py-1 w-24 text-right text-emerald-400 focus:outline-none focus:border-emerald-500"
                  onChange={(e) => updateLineItem(idx, parseFloat(e.target.value))}
                />
              </td>
              <td className="px-4 py-3 text-right font-bold text-slate-200">
                {item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="p-6 bg-slate-950 flex justify-end items-end flex-col space-y-2">
        <div className="text-slate-500 text-[10px] uppercase font-bold tracking-widest">Total Project Price (AED)</div>
        <div className="text-5xl font-black text-emerald-500 font-mono tabular-nums">
          {boq.total_price_aed?.toLocaleString()}
        </div>
      </div>
    </div>
  );
};

export default InteractiveBOQ;