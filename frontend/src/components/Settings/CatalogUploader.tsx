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
    <div className="bg-white border border-[#e2e8f0] p-6 shadow-card rounded-xl">
      <div className="flex items-center justify-between mb-4 border-b border-[#e2e8f0] pb-3">
        <h3 className="text-sm font-bold text-[#0f172a] flex items-center gap-2">
          Supplier Catalogs
        </h3>
        <button
          onClick={downloadTemplate}
          className="flex items-center gap-2 text-xs font-medium text-[#3b82f6] hover:text-[#1e3a5f] transition-colors border border-[#e2e8f0] px-3 py-1.5 rounded-lg hover:bg-slate-50"
        >
          <Download size={12} /> Download CSV Template
        </button>
      </div>

      <div className="border-2 border-dashed border-[#e2e8f0] hover:border-[#3b82f6] bg-slate-50 p-8 text-center cursor-pointer transition-all rounded-xl group hover:bg-blue-50/50">
        <Upload size={24} className="mx-auto text-[#64748b] mb-3 group-hover:text-[#3b82f6] transition-colors" />
        <p className="text-xs font-semibold text-[#374151] mb-1">Drag & Drop Catalog CSV</p>
        <p className="text-[10px] text-[#64748b]">
          Strict typing enforced for Weight_kg_m and Perimeter_mm fields
        </p>
      </div>

      <div className="mt-4 flex items-center gap-2 bg-emerald-50 p-3 rounded-lg border border-emerald-200">
        <ShieldCheck size={14} className="text-[#10b981]" />
        <p className="text-[10px] text-emerald-700 font-medium">
          Validation Gate Active: Non-float values will trigger RFI
        </p>
      </div>
    </div>
  );
};

export default CatalogUploader;
