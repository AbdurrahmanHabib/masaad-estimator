import React, { useState } from 'react';
import { ShieldCheck, Info } from 'lucide-react';

const StructuralChecklist = () => {
  const [items, setItems] = useState([
    { id: 'fs', label: 'Fire-stops (4hr Integrity)', checked: true },
    { id: 'np', label: 'Nylon Pads (Isolation)', checked: true },
    { id: 'sb', label: 'Steel Brackets (Hot-dip Galv)', checked: false },
    { id: 'av', label: 'Anti-vibration Gaskets', checked: true },
    { id: 'ep', label: 'EPDM Seals (Double Barrier)', checked: false },
  ]);

  const toggle = (id: string) => {
    setItems(items.map(i => i.id === id ? { ...i, checked: !i.checked } : i));
  };

  return (
    <div className="bg-ms-panel border border-ms-border rounded-sm overflow-hidden shadow-2xl h-full">
      <div className="p-4 bg-ms-dark border-b border-ms-border flex justify-between items-center">
        <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 italic flex items-center gap-2">
          <ShieldCheck size={14} className="text-ms-emerald" /> Structural_Protocol_Audit
        </h2>
      </div>
      
      <div className="p-6 space-y-4 overflow-y-auto">
        {items.map(item => (
          <div 
            key={item.id} 
            onClick={() => toggle(item.id)}
            className={`flex items-center justify-between p-4 border rounded-sm transition-all cursor-pointer ${item.checked ? 'bg-ms-emerald/5 border-ms-emerald/30' : 'bg-ms-dark border-ms-border opacity-60'}`}
          >
            <span className={`text-[10px] font-black uppercase tracking-widest ${item.checked ? 'text-ms-emerald' : 'text-slate-500'}`}>
              {item.label}
            </span>
            <div className={`w-4 h-4 border rounded-sm flex items-center justify-center transition-all ${item.checked ? 'bg-ms-emerald border-ms-emerald' : 'border-slate-700'}`}>
              {item.checked && <div className="w-2 h-2 bg-black rounded-xxs"></div>}
            </div>
          </div>
        ))}

        <div className="mt-8 p-4 bg-ms-amber/5 border border-ms-amber/20 rounded-sm flex items-start gap-3">
          <Info size={16} className="text-ms-amber shrink-0 mt-0.5" />
          <p className="text-[9px] font-mono text-ms-amber leading-relaxed uppercase tracking-tighter">
            System_Alert: Mandatory_Fire_Stops are required for Burj_Khalifa Zone_A Compliance. 
            AI detected missing steel bracket provisioning in Section_08.
          </p>
        </div>
      </div>
    </div>
  );
};

export default StructuralChecklist;