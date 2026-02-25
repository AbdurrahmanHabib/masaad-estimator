import React from 'react';
import { QrCode, Container, CheckCircle2 } from 'lucide-react';

const LogisticsTracker = ({ floors = 12 }: { floors?: number }) => {
  const elevations = ['E1_EAST', 'E2_WEST', 'E3_NORTH', 'E4_SOUTH'];
  
  return (
    <div className="bg-slate-900 border border-slate-800 p-8 rounded-sm shadow-2xl">
      <div className="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-sm font-black uppercase tracking-widest text-white italic">4D_Spatial_Matrix</h3>
          <p className="text-[9px] text-slate-500 font-mono mt-1 uppercase tracking-[0.2em]">Container Export Synchronization</p>
        </div>
        <button className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-black px-4 py-2 text-[10px] font-black uppercase tracking-widest transition-all">
          <QrCode size={14} /> Generate_QR_Manifest
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 border border-slate-800 text-[9px] font-mono text-slate-600 bg-slate-950">FLOOR_ID</th>
              {elevations.map(e => (
                <th key={e} className="p-3 border border-slate-800 text-[10px] font-black text-slate-400 bg-slate-900/50 uppercase tracking-tighter">
                  {e}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: floors }).map((_, i) => {
              const floorNum = floors - i;
              return (
                <tr key={floorNum}>
                  <td className="p-2 border border-slate-800 bg-slate-950 text-[10px] font-mono font-bold text-slate-500 text-center">
                    F{String(floorNum).padStart(2, '0')}
                  </td>
                  {elevations.map(e => (
                    <td key={`${floorNum}-${e}`} className="p-1 border border-slate-800 bg-slate-950/20 group cursor-pointer hover:bg-emerald-500/10 transition-colors">
                      <div className="h-8 flex items-center justify-center relative">
                        {/* Heatmap Simulation */}
                        <div className={`w-full h-full ${floorNum < 5 ? 'bg-emerald-500/20' : 'bg-slate-800/20'}`}></div>
                        {floorNum < 5 && <CheckCircle2 size={12} className="absolute text-emerald-500 opacity-50" />}
                      </div>
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-6">
        <div className="p-4 bg-slate-950 border border-slate-800 flex items-center gap-4">
          <Container className="text-ms-glass" size={24} />
          <div>
            <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Active_Shipments</span>
            <span className="text-xl font-mono font-black text-white">03_CONTAINERS</span>
          </div>
        </div>
        <div className="p-4 bg-slate-950 border border-slate-800 flex items-center gap-4 opacity-50 italic">
          <p className="text-[9px] text-slate-600 leading-tight">
            // Note: Afghan subcontractor receiving "Fix_01_Brackets" manifest. <br/>
            // Factory assembly restricted from export view.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LogisticsTracker;