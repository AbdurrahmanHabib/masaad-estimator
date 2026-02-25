import React from 'react';
import { FileText, Download, Scissors, Shield } from 'lucide-react';

const ExportCenter = ({ project_id }: { project_id: string }) => {
  return (
    <div className="bg-white border-t border-slate-100 w-80 p-6 space-y-6 flex flex-col z-10">
      <div>
        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-6 flex items-center gap-2">
          <Download size={12} /> Export_Control_Center
        </h3>
        
        <div className="space-y-3">
          <button className="w-full flex items-center justify-between p-4 bg-ms-primary text-white hover:bg-ms-dark transition-all rounded-sm group">
            <div className="text-left">
              <span className="block text-[10px] font-bold opacity-60 uppercase tracking-tighter">Technical_Submittal</span>
              <span className="text-[11px] font-black uppercase tracking-tight">Shop_Drawings.PDF</span>
            </div>
            <FileText size={18} className="opacity-40 group-hover:opacity-100" />
          </button>

          <button className="w-full flex items-center justify-between p-4 border border-ms-primary text-ms-primary hover:bg-slate-50 transition-all rounded-sm group">
            <div className="text-left">
              <span className="block text-[10px] font-bold opacity-60 uppercase tracking-tighter">Commercial_Quote</span>
              <span className="text-[11px] font-black uppercase tracking-tight">Formal_BOQ_v1.PDF</span>
            </div>
            <Download size={18} className="opacity-40 group-hover:opacity-100" />
          </button>
        </div>
      </div>

      <div className="pt-6 border-t border-slate-100">
        <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-4 flex items-center gap-2">
          <Shield size={12} /> Internal_Production
        </h3>
        
        <button className="w-full flex items-center justify-between p-4 bg-slate-50 text-slate-400 hover:bg-slate-100 transition-all rounded-sm group">
          <div className="text-left">
            <span className="block text-[10px] font-bold opacity-60 uppercase tracking-tighter">Factory_Use_Only</span>
            <span className="text-[11px] font-black uppercase tracking-tight">Cutting_List.CSV</span>
          </div>
          <Scissors size={18} className="opacity-30 group-hover:opacity-100" />
        </button>
      </div>
    </div>
  );
};

export default ExportCenter;