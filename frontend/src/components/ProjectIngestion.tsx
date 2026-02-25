import React, { useState, useRef } from 'react';
import { Upload, FileText, Settings, AlertCircle, Play, Loader2, CheckCircle2 } from 'lucide-react';

const ProjectIngestion = () => {
  const [pricing, setPricing] = useState({
    billetPremium: 450,
    extrusionMargin: 2.5,
    adminPct: 8,
    factoryPct: 12,
    riskPct: 5,
    profitPct: 15
  });

  const [drawingsFile, setDrawingsFile] = useState<File | null>(null);
  const [specsFile, setSpecsFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{drawings?: 'idle' | 'success' | 'error', specs?: 'idle' | 'success' | 'error'}>({});

  const drawingsInputRef = useRef<HTMLInputElement>(null);
  const specsInputRef = useRef<HTMLInputElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleFileChange = (type: 'drawings' | 'specs', e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (type === 'drawings') setDrawingsFile(file);
      else setSpecsFile(file);
      setUploadStatus(prev => ({ ...prev, [type]: 'idle' }));
    }
  };

  const executeFusion = async () => {
    if (!drawingsFile || !specsFile) {
      alert("Please upload both Drawings and Specifications before executing Fusion.");
      return;
    }

    setIsProcessing(true);
    try {
      // 1. Upload Drawings
      const drawingsFormData = new FormData();
      drawingsFormData.append('file', drawingsFile);
      const drawingsRes = await fetch(`${API_URL}/api/ingestion/upload-drawings`, {
        method: 'POST',
        body: drawingsFormData
      });
      if (!drawingsRes.ok) throw new Error("Drawings upload failed");
      const drawingsData = await drawingsRes.json();
      setUploadStatus(prev => ({ ...prev, drawings: 'success' }));

      // 2. Upload Specs
      const specsFormData = new FormData();
      specsFormData.append('file', specsFile);
      const specsRes = await fetch(`${API_URL}/api/ingestion/upload-specs`, {
        method: 'POST',
        body: specsFormData
      });
      if (!specsRes.ok) throw new Error("Specs upload failed");
      const specsData = await specsRes.json();
      setUploadStatus(prev => ({ ...prev, specs: 'success' }));

      // 3. Execute Fusion Engine
      const fusionRes = await fetch(`${API_URL}/api/ingestion/execute-fusion`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          drawings_id: drawingsData.file_id,
          specs_id: specsData.file_id,
          pricing_matrix: pricing
        })
      });
      if (!fusionRes.ok) throw new Error("Fusion execution failed");
      
      alert("Fusion Engine Executed Successfully! Processing in background.");
    } catch (err) {
      console.error(err);
      alert("An error occurred during fusion execution.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-ms-dark p-10 text-slate-200 font-sans h-full overflow-y-auto">
      <div className="mb-8 border-b border-ms-border pb-4 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black uppercase tracking-tighter text-ms-emerald italic">Omniscient Ingestion</h2>
          <p className="text-[10px] text-slate-500 font-mono mt-1 uppercase tracking-[0.2em]">UAE True-Cost Market Model</p>
        </div>
        <button 
          onClick={executeFusion}
          disabled={isProcessing}
          className="flex items-center gap-2 bg-ms-emerald hover:bg-emerald-600 disabled:bg-slate-800 text-black px-6 py-3 rounded-sm font-bold uppercase text-[10px] tracking-widest transition-all shadow-xl shadow-ms-emerald/20"
        >
          {isProcessing ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} 
          {isProcessing ? 'Processing...' : 'Execute Fusion Engine'}
        </button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 mb-10">
        
        {/* DUAL UPLOAD ZONE */}
        <div className="space-y-6">
          <input type="file" ref={drawingsInputRef} className="hidden" accept=".dwg,.dxf" onChange={(e) => handleFileChange('drawings', e)} />
          <div 
            onClick={() => drawingsInputRef.current?.click()}
            className={`bg-ms-panel border-2 border-dashed p-8 rounded text-center transition-all cursor-pointer group ${drawingsFile ? 'border-ms-emerald bg-ms-emerald/5' : 'border-ms-border hover:border-ms-emerald'}`}
          >
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4 flex items-center justify-center gap-2">
              <Upload size={14} className={drawingsFile ? 'text-ms-emerald' : 'text-slate-600'} /> 1. Upload Drawings (CAD/DWG)
            </h3>
            <p className={`text-sm font-bold ${drawingsFile ? 'text-white' : 'text-slate-400'} group-hover:text-ms-emerald transition-colors`}>
              {drawingsFile ? drawingsFile.name : 'Click or drag .DWG files'}
            </p>
            {drawingsFile && (
              <div className="mt-4 flex items-center justify-center gap-2 text-ms-emerald text-[10px] font-black uppercase tracking-widest">
                <CheckCircle2 size={12} /> Ready for Fusion
              </div>
            )}
            {!drawingsFile && <p className="text-[10px] text-slate-600 mt-2 font-mono uppercase">Extracts Quantities, Dimensions & Blocks</p>}
          </div>

          <input type="file" ref={specsInputRef} className="hidden" accept=".pdf" onChange={(e) => handleFileChange('specs', e)} />
          <div 
            onClick={() => specsInputRef.current?.click()}
            className={`bg-ms-panel border-2 border-dashed p-8 rounded text-center transition-all cursor-pointer group ${specsFile ? 'border-ms-amber bg-ms-amber/5' : 'border-ms-border hover:border-ms-amber'}`}
          >
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4 flex items-center justify-center gap-2">
              <FileText size={14} className={specsFile ? 'text-ms-amber' : 'text-slate-600'} /> 2. Upload Specifications (PDF/Word)
            </h3>
            <p className={`text-sm font-bold ${specsFile ? 'text-white' : 'text-slate-400'} group-hover:text-ms-amber transition-colors`}>
              {specsFile ? specsFile.name : 'Click or drag .PDF files'}
            </p>
            {specsFile && (
              <div className="mt-4 flex items-center justify-center gap-2 text-ms-amber text-[10px] font-black uppercase tracking-widest">
                <CheckCircle2 size={12} /> Ready for Fusion
              </div>
            )}
            {!specsFile && <p className="text-[10px] text-slate-600 mt-2 font-mono uppercase">Extracts U-Values, Finishes & Hardware Brands</p>}
          </div>
        </div>

        {/* UAE PRICING MATRIX */}
        <div className="bg-ms-panel border border-ms-border p-8 flex flex-col h-full rounded-sm shadow-2xl">
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-ms-emerald mb-6 flex items-center gap-2 border-b border-ms-border pb-4 italic">
            <Settings size={14} className="text-ms-emerald" /> UAE True-Cost Matrix
          </h3>
          
          <div className="space-y-8 flex-1">
            {/* Supplier Margins */}
            <div>
              <h4 className="text-[9px] font-black uppercase text-slate-500 mb-4 tracking-wider">Supplier Margins (Live Negotiation)</h4>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-500 mb-2">Billet Premium (USD/MT)</label>
                  <input type="number" value={pricing.billetPremium} onChange={e => setPricing({...pricing, billetPremium: Number(e.target.value)})} className="w-full bg-ms-dark border border-ms-border rounded-sm p-3 text-sm font-mono text-ms-emerald focus:outline-none focus:border-ms-emerald transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-500 mb-2">Extrusion Cost (AED/KG)</label>
                  <input type="number" value={pricing.extrusionMargin} onChange={e => setPricing({...pricing, extrusionMargin: Number(e.target.value)})} className="w-full bg-ms-dark border border-ms-border rounded-sm p-3 text-sm font-mono text-ms-emerald focus:outline-none focus:border-ms-emerald transition-all" />
                </div>
              </div>
            </div>

            {/* Dynamic Overheads */}
            <div>
              <h4 className="text-[9px] font-black uppercase text-slate-500 mb-4 tracking-wider mt-2">Dynamic Overhead Profile (%)</h4>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-500 mb-2">Admin Overhead %</label>
                  <input type="number" value={pricing.adminPct} onChange={e => setPricing({...pricing, adminPct: Number(e.target.value)})} className="w-full bg-ms-dark border border-ms-border rounded-sm p-3 text-sm font-mono text-white focus:outline-none focus:border-ms-emerald transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-500 mb-2">Factory Overhead %</label>
                  <input type="number" value={pricing.factoryPct} onChange={e => setPricing({...pricing, factoryPct: Number(e.target.value)})} className="w-full bg-ms-dark border border-ms-border rounded-sm p-3 text-sm font-mono text-white focus:outline-none focus:border-ms-emerald transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-500 mb-2">Risk Contingency %</label>
                  <input type="number" value={pricing.riskPct} onChange={e => setPricing({...pricing, riskPct: Number(e.target.value)})} className="w-full bg-ms-dark border border-ms-border rounded-sm p-3 text-sm font-mono text-white focus:outline-none focus:border-ms-emerald transition-all" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-500 mb-2">Target Profit %</label>
                  <input type="number" value={pricing.profitPct} onChange={e => setPricing({...pricing, profitPct: Number(e.target.value)})} className="w-full bg-ms-dark border border-ms-border rounded-sm p-3 text-sm font-mono text-white focus:outline-none focus:border-ms-emerald transition-all" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* RFI Warning Example */}
      <div className="bg-ms-amber/5 border border-ms-amber/20 p-5 rounded-sm flex items-start gap-4 shadow-sm">
        <AlertCircle size={20} className="text-ms-amber mt-0.5 shrink-0 animate-pulse" />
        <div>
          <h4 className="text-[11px] font-black text-ms-amber uppercase tracking-widest">System RFI Generated</h4>
          <p className="text-xs font-mono text-slate-400 mt-2 leading-relaxed">
            [DWG_LAYER_A-102] indicates System <span className="font-bold text-white">"SD-01"</span> (Sliding Door). 
            <br/>[PDF_SPEC_SECTION_08410] is missing Hardware Brand requirement. 
            <br/>Status flagged as <span className="bg-ms-amber text-black px-2 py-0.5 rounded font-black ml-1">RFI_REQUIRED</span>
          </p>
        </div>
      </div>
      
    </div>
  );
};

export default ProjectIngestion;