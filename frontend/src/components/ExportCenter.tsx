import React from 'react';
import { FileText, Download, Scissors, Shield } from 'lucide-react';

const ExportCenter = ({ project_id }: { project_id: string }) => {
  return (
    <div className="space-y-6">
      <div>
        <div className="space-y-3">
          <button className="w-full flex items-center justify-between p-4 bg-ms-emerald hover:bg-emerald-600 text-black transition-all rounded-sm group shadow-lg shadow-ms-emerald/5">
            <div className="text-left">
              <span className="block text-[8px] font-black opacity-70 uppercase tracking-widest">Technical_Submittal</span>
              <span className="text-[10px] font-black uppercase tracking-[0.1em]">Generate_Shop_Drawings</span>
            </div>
            <FileText size={16} className="opacity-70 group-hover:opacity-100" />
          </button>

          <button className="w-full flex items-center justify-between p-4 bg-ms-panel border border-ms-border text-slate-300 hover:border-ms-emerald/50 hover:bg-ms-dark transition-all rounded-sm group">
            <div className="text-left">
              <span className="block text-[8px] font-black opacity-50 uppercase tracking-widest">Commercial_Quote</span>
              <span className="text-[10px] font-black uppercase tracking-[0.1em]">Export_Formal_BOQ</span>
            </div>
            <Download size={16} className="opacity-40 group-hover:opacity-100" />
          </button>
        </div>
      </div>

      <div className="pt-6 border-t border-ms-border">
        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 mb-4 flex items-center gap-2 italic">
          <Shield size={12} /> Production_Release
        </h3>
        
        <button className="w-full flex items-center justify-between p-4 bg-ms-dark/40 border border-ms-border text-slate-500 hover:text-slate-300 hover:border-ms-amber/50 transition-all rounded-sm group">
          <div className="text-left">
            <span className="block text-[8px] font-black opacity-50 uppercase tracking-widest text-ms-amber">Factory_Provisioning</span>
            <span className="text-[10px] font-black uppercase tracking-[0.1em]">Download_Cutting_List</span>
          </div>
          <Scissors size={16} className="opacity-30 group-hover:opacity-100 group-hover:text-ms-amber" />
        </button>
      </div>
    </div>
  );
};

export default ExportCenter;