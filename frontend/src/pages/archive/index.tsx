import React from 'react';

export default function Archive() {
  return (
    <div className="flex-1 overflow-y-auto p-10 bg-ms-dark">
      <div className="mb-8 border-b border-ms-border pb-4">
        <h2 className="text-3xl font-black uppercase tracking-tighter text-ms-emerald italic">Project Archive</h2>
        <p className="text-[10px] text-slate-500 font-mono mt-1 uppercase tracking-[0.2em]">Historical Estimation Data</p>
      </div>
      
      <div className="bg-ms-panel border border-ms-border p-20 text-center rounded-sm">
        <p className="text-slate-500 font-mono text-xs uppercase tracking-widest">No archived projects found in the vault.</p>
      </div>
    </div>
  );
}
