import React, { useState, useRef } from 'react';
import { useRouter } from 'next/router';
import {
  Upload, FileText, Play, Loader2, CheckCircle2, AlertCircle,
  MapPin, Building2, Globe, Sliders,
} from 'lucide-react';
import { getAuthHeaders } from '../store/useAuthStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const ProjectIngestion = () => {
  const router = useRouter();

  const [projectName, setProjectName] = useState('');
  const [clientName, setClientName] = useState('');
  const [location, setLocation] = useState('Dubai, UAE');
  const [country, setCountry] = useState('UAE');
  const [complexity, setComplexity] = useState(1.0);
  const [scopeBoundary, setScopeBoundary] = useState('Panels + Substructure');

  const [dwgFile, setDwgFile] = useState<File | null>(null);
  const [specFile, setSpecFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dwgRef = useRef<HTMLInputElement>(null);
  const specRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async () => {
    if (!projectName.trim()) { setError('Project name is required.'); return; }
    if (!dwgFile && !specFile) { setError('Upload at least one file (DWG or PDF spec).'); return; }

    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('project_name', projectName.trim());
      formData.append('client_name', clientName.trim());
      formData.append('project_location', location.trim());
      formData.append('project_country', country.trim());
      formData.append('complexity_multiplier', String(complexity));
      formData.append('scope_boundary', scopeBoundary);
      if (dwgFile) formData.append('dwg_file', dwgFile);
      if (specFile) formData.append('spec_file', specFile);

      const authHeaders = getAuthHeaders();
      const res = await fetch(`${API_URL}/api/ingestion/new-project`, {
        method: 'POST',
        body: formData,
        headers: authHeaders as HeadersInit,
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => 'Unknown error');
        throw new Error(`Server error ${res.status}: ${txt}`);
      }

      const data = await res.json();
      router.push(`/estimate/${data.estimate_id}`);
    } catch (err) {
      setError(String(err));
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* Header */}
        <div>
          <h2 className="text-xl font-black text-slate-800 uppercase tracking-tight">New Estimate</h2>
          <p className="text-xs text-slate-500 mt-1">Upload drawings + specs to start AI-powered estimation</p>
        </div>

        {/* Project Details */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Building2 size={16} className="text-blue-600" />
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700">Project Details</h3>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                Project Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g. Al Kabir Tower — Curtain Wall"
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">Client Name</label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="e.g. Al Kabir Developments LLC"
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                <MapPin size={10} className="inline mr-1" /> Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                <Globe size={10} className="inline mr-1" /> Country
              </label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {['UAE', 'Saudi Arabia', 'Qatar', 'Kuwait', 'Bahrain', 'Oman', 'Egypt', 'Other'].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">
                <Sliders size={10} className="inline mr-1" /> Complexity Multiplier
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={0.5}
                  max={2.0}
                  step={0.1}
                  value={complexity}
                  onChange={(e) => setComplexity(Number(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-mono font-bold text-blue-600 w-8">{complexity.toFixed(1)}×</span>
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">Scope Boundary</label>
              <select
                value={scopeBoundary}
                onChange={(e) => setScopeBoundary(e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                {[
                  'Panels Only',
                  'Panels + Substructure',
                  'Full Supply & Install',
                  'Design + Supply + Install',
                ].map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </div>

        {/* File Upload */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Upload size={16} className="text-blue-600" />
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700">Upload Files</h3>
            <span className="text-[10px] text-slate-400 ml-auto">At least one file required</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* DWG */}
            <input ref={dwgRef} type="file" accept=".dwg,.dxf" className="hidden" onChange={(e) => setDwgFile(e.target.files?.[0] ?? null)} />
            <button
              type="button"
              onClick={() => dwgRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all hover:border-blue-400 ${dwgFile ? 'border-emerald-400 bg-emerald-50' : 'border-slate-200 hover:bg-blue-50'}`}
            >
              {dwgFile ? (
                <>
                  <CheckCircle2 size={24} className="mx-auto text-emerald-500 mb-2" />
                  <p className="text-xs font-bold text-emerald-700 truncate px-2">{dwgFile.name}</p>
                  <p className="text-[10px] text-emerald-500 mt-1">{(dwgFile.size / 1024).toFixed(0)} KB</p>
                </>
              ) : (
                <>
                  <Upload size={24} className="mx-auto text-slate-300 mb-2" />
                  <p className="text-xs font-semibold text-slate-600">DWG / DXF Drawing</p>
                  <p className="text-[10px] text-slate-400 mt-1">Click to browse</p>
                </>
              )}
            </button>

            {/* PDF Spec */}
            <input ref={specRef} type="file" accept=".pdf,.docx,.doc" className="hidden" onChange={(e) => setSpecFile(e.target.files?.[0] ?? null)} />
            <button
              type="button"
              onClick={() => specRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${specFile ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-blue-400 hover:bg-blue-50'}`}
            >
              {specFile ? (
                <>
                  <CheckCircle2 size={24} className="mx-auto text-blue-500 mb-2" />
                  <p className="text-xs font-bold text-blue-700 truncate px-2">{specFile.name}</p>
                  <p className="text-[10px] text-blue-500 mt-1">{(specFile.size / 1024).toFixed(0)} KB</p>
                </>
              ) : (
                <>
                  <FileText size={24} className="mx-auto text-slate-300 mb-2" />
                  <p className="text-xs font-semibold text-slate-600">PDF / DOCX Specification</p>
                  <p className="text-[10px] text-slate-400 mt-1">Click to browse</p>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
            <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={isProcessing}
          className="w-full flex items-center justify-center gap-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white py-4 rounded-xl font-bold uppercase text-sm tracking-widest transition-all shadow-lg shadow-blue-600/20"
        >
          {isProcessing ? (
            <><Loader2 size={18} className="animate-spin" /> Submitting…</>
          ) : (
            <><Play size={18} /> Start Estimation Pipeline</>
          )}
        </button>
      </div>
    </div>
  );
};

export default ProjectIngestion;
