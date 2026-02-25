import React, { useState } from 'react';
import { Upload, FileText, Settings, AlertCircle, Play } from 'lucide-react';

const ProjectIngestion = () => {
  const [pricing, setPricing] = useState({
    billetPremium: 450,
    extrusionMargin: 2.5,
    adminPct: 8,
    factoryPct: 12,
    riskPct: 5,
    profitPct: 15
  });

  return (
    <div className="bg-ms-bg p-10 text-ms-dark font-sans h-full overflow-y-auto">
      <div className="mb-8 border-b border-slate-200 pb-4 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black uppercase tracking-tighter text-ms-primary italic">Omniscient Ingestion</h2>
          <p className="text-[10px] text-slate-500 font-mono mt-1 uppercase tracking-[0.2em]">UAE True-Cost Market Model</p>
        </div>
        <button className="flex items-center gap-2 bg-ms-primary hover:bg-ms-dark text-white px-6 py-3 rounded-sm font-bold uppercase text-[10px] tracking-widest transition-all shadow-xl shadow-ms-primary/20">
          <Play size={14} className="text-ms-accent" /> Execute Fusion Engine
        </button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 mb-10">
        
        {/* DUAL UPLOAD ZONE */}
        <div className="space-y-6">
          <div className="glass-panel p-6">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4 flex items-center gap-2">
              <Upload size={14} className="text-ms-glass" /> 1. Upload Drawings (CAD/DWG)
            </h3>
            <div className="border-2 border-dashed border-slate-300 rounded p-10 text-center hover:border-ms-glass transition-colors cursor-pointer bg-slate-50/50 group">
              <p className="text-sm font-bold text-ms-primary group-hover:text-ms-glass transition-colors">Drag & Drop .DWG files</p>
              <p className="text-[10px] text-slate-400 mt-2 font-mono uppercase">Extracts Quantities, Dimensions & Blocks</p>
            </div>
          </div>

          <div className="glass-panel p-6">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4 flex items-center gap-2">
              <FileText size={14} className="text-ms-glass" /> 2. Upload Specifications (PDF/Word)
            </h3>
            <div className="border-2 border-dashed border-slate-300 rounded p-10 text-center hover:border-ms-glass transition-colors cursor-pointer bg-slate-50/50 group">
              <p className="text-sm font-bold text-ms-primary group-hover:text-ms-glass transition-colors">Drag & Drop .PDF files</p>
              <p className="text-[10px] text-slate-400 mt-2 font-mono uppercase">Extracts U-Values, Finishes & Hardware Brands</p>
            </div>
          </div>
        </div>

        {/* UAE PRICING MATRIX */}
        <div className="glass-panel p-8 flex flex-col h-full">
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-ms-primary mb-6 flex items-center gap-2 border-b border-slate-200 pb-4">
            <Settings size={14} className="text-ms-accent" /> UAE True-Cost Matrix
          </h3>
          
          <div className="space-y-8 flex-1">
            {/* Supplier Margins */}
            <div>
              <h4 className="text-[9px] font-black uppercase text-slate-400 mb-4 tracking-wider">Supplier Margins (Live Negotiation)</h4>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-600 mb-2">Billet Premium (USD/MT)</label>
                  <input type="number" value={pricing.billetPremium} onChange={e => setPricing({...pricing, billetPremium: Number(e.target.value)})} className="w-full border border-slate-300 rounded-sm p-3 text-sm font-mono text-ms-primary focus:outline-none focus:border-ms-glass focus:ring-1 focus:ring-ms-glass/50 transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-600 mb-2">Extrusion Cost (AED/KG)</label>
                  <input type="number" value={pricing.extrusionMargin} onChange={e => setPricing({...pricing, extrusionMargin: Number(e.target.value)})} className="w-full border border-slate-300 rounded-sm p-3 text-sm font-mono text-ms-primary focus:outline-none focus:border-ms-glass focus:ring-1 focus:ring-ms-glass/50 transition-all" />
                </div>
              </div>
            </div>

            {/* Dynamic Overheads */}
            <div>
              <h4 className="text-[9px] font-black uppercase text-slate-400 mb-4 tracking-wider mt-2">Dynamic Overhead Profile (%)</h4>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-600 mb-2">Admin Overhead %</label>
                  <input type="number" value={pricing.adminPct} onChange={e => setPricing({...pricing, adminPct: Number(e.target.value)})} className="w-full border border-slate-300 rounded-sm p-3 text-sm font-mono text-ms-primary focus:outline-none focus:border-ms-glass focus:ring-1 focus:ring-ms-glass/50 transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-600 mb-2">Factory Overhead %</label>
                  <input type="number" value={pricing.factoryPct} onChange={e => setPricing({...pricing, factoryPct: Number(e.target.value)})} className="w-full border border-slate-300 rounded-sm p-3 text-sm font-mono text-ms-primary focus:outline-none focus:border-ms-glass focus:ring-1 focus:ring-ms-glass/50 transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-600 mb-2">Risk Contingency %</label>
                  <input type="number" value={pricing.riskPct} onChange={e => setPricing({...pricing, riskPct: Number(e.target.value)})} className="w-full border border-slate-300 rounded-sm p-3 text-sm font-mono text-ms-primary focus:outline-none focus:border-ms-glass focus:ring-1 focus:ring-ms-glass/50 transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-600 mb-2">Target Profit %</label>
                  <input type="number" value={pricing.profitPct} onChange={e => setPricing({...pricing, profitPct: Number(e.target.value)})} className="w-full border border-slate-300 rounded-sm p-3 text-sm font-mono text-ms-primary focus:outline-none focus:border-ms-glass focus:ring-1 focus:ring-ms-glass/50 transition-all" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* RFI Warning Example */}
      <div className="bg-[#fff7ed] border border-[#ffedd5] p-5 rounded-sm flex items-start gap-4 shadow-sm">
        <AlertCircle size={20} className="text-ms-accent mt-0.5 shrink-0 animate-pulse" />
        <div>
          <h4 className="text-[11px] font-black text-[#ea580c] uppercase tracking-widest">System RFI Generated</h4>
          <p className="text-xs font-mono text-[#9a3412] mt-2 leading-relaxed">
            [DWG_LAYER_A-102] indicates System <span className="font-bold">"SD-01"</span> (Sliding Door). 
            <br/>[PDF_SPEC_SECTION_08410] is missing Hardware Brand requirement. 
            <br/>Status flagged as <span className="bg-[#ea580c] text-white px-2 py-0.5 rounded font-bold ml-1">RFI_REQUIRED</span>
          </p>
        </div>
      </div>
      
    </div>
  );
};

export default ProjectIngestion;