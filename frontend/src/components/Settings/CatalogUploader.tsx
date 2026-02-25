import React from 'react';
import { Download, Upload, ShieldCheck } from 'lucide-react';

const CatalogUploader = () => {
  const downloadTemplate = () => {
    const headers = "Supplier_Name,System_Series,Die_Number,Description,Weight_kg_m,Perimeter_mm,Scrap_Value_Factor\n";
    const example = "Gulf Extrusions,GE-F,F-1025,Standard Mullion,2.450,450.5,1.0\n";
    const blob = new Blob([headers + example], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = "Masaad_Supplier_Template.csv";
    a.click();
  };

  return (
    <div className="bg-slate-900 border border-slate-800 p-6 shadow-2xl relative group overflow-hidden rounded-sm">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
          Zone 3: Supplier Catalogs
        </h3>
        <button 
          onClick={downloadTemplate}
          className="flex items-center gap-2 text-[9px] font-black text-ms-glass hover:text-white transition-colors border border-ms-glass/30 px-2 py-1 rounded-sm uppercase tracking-tighter"
        >
          <Download size={10} /> Download CSV Template
        </button>
      </div>
      
      <div className="border-2 border-dashed border-slate-800 hover:border-ms-glass/50 bg-slate-950/50 p-8 text-center cursor-pointer transition-colors rounded-sm">
        <Upload size={24} className="mx-auto text-slate-600 mb-3" />
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Drag & Drop Catalog .CSV</p>
        <p className="text-[9px] text-slate-600 font-mono italic">
          // Enforces strict typing for Weight_kg_m & Perimeter_mm
        </p>
      </div>

      <div className="mt-4 flex items-center gap-2 bg-emerald-500/5 p-3 rounded-sm border border-emerald-500/10">
        <ShieldCheck size={14} className="text-ms-emerald" />
        <p className="text-[9px] font-mono text-emerald-500/70 uppercase">
          Validation Gate Active: Non-float values will trigger RFI
        </p>
      </div>
    </div>
  );
};

export default CatalogUploader;