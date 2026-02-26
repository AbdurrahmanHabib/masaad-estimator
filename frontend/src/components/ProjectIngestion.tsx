import React, { useState, useRef } from 'react';
import { useRouter } from 'next/router';
import {
  Upload, FileText, Play, Loader2, CheckCircle2, AlertCircle,
  MapPin, Building2, Globe, Sliders, FileWarning, ClipboardList,
  ChevronDown, ChevronUp,
} from 'lucide-react';
import { getAuthHeaders } from '../store/useAuthStore';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const INPUT_CLS = 'w-full border border-[#e2e8f0] rounded-md px-3 py-2 text-sm text-[#1e293b] focus:outline-none focus:ring-2 focus:ring-[#002147]/20 focus:border-[#002147] bg-white transition-all';
const LABEL_CLS = 'block text-xs font-semibold text-[#002147] mb-1';
const SELECT_CLS = `${INPUT_CLS} appearance-none`;

const COUNTRIES = [
  'UAE', 'Saudi Arabia', 'Qatar', 'Kuwait', 'Bahrain', 'Oman',
  'Egypt', 'Jordan', 'Iraq', 'Turkey', 'India', 'Pakistan', 'Other',
];

const SCOPE_OPTIONS = [
  'Supply Only',
  'Supply + Fabricate',
  'Panels + Substructure',
  'Full Supply & Install',
  'Design + Supply + Install',
];

const CONTRACT_TYPES = [
  'Supply Only',
  'Supply + Fabricate',
  'Supply + Fabricate + Install',
  'Design + Supply + Fabricate + Install',
  'Nominated Subcontractor',
];

const SITE_CONDITIONS = [
  { value: 'standard', label: 'Standard access' },
  { value: 'high_rise', label: 'High-rise (above 40m) — crane required' },
  { value: 'restricted', label: 'Restricted access — manual handling' },
  { value: 'coastal', label: 'Coastal / corrosive environment — marine grade' },
  { value: 'desert', label: 'Desert / extreme heat — thermal considerations' },
  { value: 'occupied', label: 'Occupied building — working hours restrictions' },
];

const ProjectIngestion = () => {
  const router = useRouter();

  // Core fields
  const [projectName, setProjectName] = useState('');
  const [clientName, setClientName] = useState('');
  const [location, setLocation] = useState('Dubai, UAE');
  const [country, setCountry] = useState('UAE');
  const [complexity, setComplexity] = useState(1.0);
  const [scopeBoundary, setScopeBoundary] = useState('Panels + Substructure');
  const [contractType, setContractType] = useState('Supply + Fabricate + Install');

  // Additional context
  const [siteConditions, setSiteConditions] = useState<string[]>([]);
  const [specNotes, setSpecNotes] = useState('');
  const [exclusions, setExclusions] = useState('');
  const [estimatorNotes, setEstimatorNotes] = useState('');
  const [budgetCap, setBudgetCap] = useState('');
  const [deliveryWeeks, setDeliveryWeeks] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Files
  const [dwgFile, setDwgFile] = useState<File | null>(null);
  const [specFile, setSpecFile] = useState<File | null>(null);
  const [extraFile, setExtraFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dwgRef = useRef<HTMLInputElement>(null);
  const specRef = useRef<HTMLInputElement>(null);
  const extraRef = useRef<HTMLInputElement>(null);

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
      formData.append('contract_type', contractType);
      formData.append('site_conditions', siteConditions.join(', '));
      formData.append('specification_notes', specNotes.trim());
      formData.append('known_exclusions', exclusions.trim());
      formData.append('estimator_notes', estimatorNotes.trim());
      if (budgetCap) formData.append('budget_cap_aed', budgetCap);
      if (deliveryWeeks) formData.append('delivery_weeks', deliveryWeeks);
      if (dwgFile) formData.append('dwg_file', dwgFile);
      if (specFile) formData.append('spec_file', specFile);
      if (extraFile) formData.append('extra_file', extraFile);

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

      // Auto-trigger pipeline if no Celery worker
      if (data.status === 'queued_no_worker') {
        try {
          await fetch(`${API_URL}/api/ingestion/run-pipeline`, {
            method: 'POST',
            headers: { ...authHeaders, 'Content-Type': 'application/json' } as HeadersInit,
            body: JSON.stringify({ estimate_id: data.estimate_id }),
          });
        } catch {
          // Non-fatal — pipeline can be triggered manually later
        }
      }

      router.push(`/estimate/${data.estimate_id}`);
    } catch (err) {
      setError(String(err));
      setIsProcessing(false);
    }
  };

  const toggleSiteCondition = (val: string) => {
    setSiteConditions((prev) =>
      prev.includes(val) ? prev.filter((v) => v !== val) : [...prev, val]
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-[#f8fafc]">
      <div className="max-w-3xl mx-auto space-y-5">

        {/* Header */}
        <div>
          <h2 className="text-lg font-bold text-[#1e293b]">New Estimate</h2>
          <p className="text-sm text-[#64748b] mt-0.5">Upload drawings and specifications to start AI-powered estimation.</p>
        </div>

        {/* Project Details */}
        <div className="bg-white rounded-md border border-[#e2e8f0] p-5 space-y-4 shadow-sm">
          <div className="flex items-center gap-2 pb-2 border-b border-[#e2e8f0]">
            <Building2 size={16} className="text-[#002147]" />
            <h3 className="text-sm font-semibold text-[#002147]">Project Details</h3>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={LABEL_CLS}>Project Name <span className="text-red-500">*</span></label>
              <input type="text" value={projectName} onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g. Al Kabir Tower" className={INPUT_CLS} />
            </div>
            <div>
              <label className={LABEL_CLS}>Client / Consultant</label>
              <input type="text" value={clientName} onChange={(e) => setClientName(e.target.value)}
                placeholder="e.g. BIR Mimarlik" className={INPUT_CLS} />
            </div>
            <div>
              <label className={LABEL_CLS}><MapPin size={12} className="inline mr-1" />Location</label>
              <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} className={INPUT_CLS} />
            </div>
            <div>
              <label className={LABEL_CLS}><Globe size={12} className="inline mr-1" />Country</label>
              <select value={country} onChange={(e) => setCountry(e.target.value)} className={SELECT_CLS}>
                {COUNTRIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className={LABEL_CLS}>Contract Type</label>
              <select value={contractType} onChange={(e) => setContractType(e.target.value)} className={SELECT_CLS}>
                {CONTRACT_TYPES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className={LABEL_CLS}>Scope Boundary</label>
              <select value={scopeBoundary} onChange={(e) => setScopeBoundary(e.target.value)} className={SELECT_CLS}>
                {SCOPE_OPTIONS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className={LABEL_CLS}><Sliders size={12} className="inline mr-1" />Complexity</label>
              <div className="flex items-center gap-2">
                <input type="range" min={0.5} max={2.0} step={0.1} value={complexity}
                  onChange={(e) => setComplexity(Number(e.target.value))} className="flex-1 h-2" />
                <span className="text-sm font-mono font-semibold text-[#002147] w-10 text-right">{complexity.toFixed(1)}x</span>
              </div>
            </div>
          </div>
        </div>

        {/* Advanced: Estimator Context */}
        <div className="bg-white rounded-md border border-[#e2e8f0] shadow-sm">
          <button type="button" onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-slate-50 transition-colors rounded-md">
            <div className="flex items-center gap-2">
              <ClipboardList size={16} className="text-[#002147]" />
              <span className="text-sm font-semibold text-[#1e293b]">Estimator Context</span>
              <span className="text-xs text-[#64748b]">(optional -- helps AI produce a more accurate estimate)</span>
            </div>
            {showAdvanced ? <ChevronUp size={16} className="text-[#64748b]" /> : <ChevronDown size={16} className="text-[#64748b]" />}
          </button>

          {showAdvanced && (
            <div className="px-5 pb-5 space-y-4 border-t border-[#e2e8f0] pt-4">
              {/* Site Conditions */}
              <div>
                <label className={LABEL_CLS}>Site Conditions</label>
                <div className="flex flex-wrap gap-2">
                  {SITE_CONDITIONS.map((sc) => (
                    <button key={sc.value} type="button" onClick={() => toggleSiteCondition(sc.value)}
                      className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${
                        siteConditions.includes(sc.value)
                          ? 'bg-blue-50 border-[#002147] text-[#002147] font-semibold'
                          : 'bg-white border-[#e2e8f0] text-[#374151] hover:border-slate-300'
                      }`}>
                      {sc.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={LABEL_CLS}>Budget Cap (AED)</label>
                  <input type="number" value={budgetCap} onChange={(e) => setBudgetCap(e.target.value)}
                    placeholder="e.g. 5000000" className={INPUT_CLS} />
                </div>
                <div>
                  <label className={LABEL_CLS}>Delivery Timeline (weeks)</label>
                  <input type="number" value={deliveryWeeks} onChange={(e) => setDeliveryWeeks(e.target.value)}
                    placeholder="e.g. 12" className={INPUT_CLS} />
                </div>
              </div>

              {/* Specification Notes */}
              <div>
                <label className={LABEL_CLS}>Specification Notes</label>
                <textarea value={specNotes} onChange={(e) => setSpecNotes(e.target.value)} rows={3}
                  placeholder="e.g. Client requires Technal curtain wall system, Guardian Low-E glass, Jotun powder coating RAL 7016, fire-rated glazing at levels 1-3"
                  className={`${INPUT_CLS} resize-none`} />
              </div>

              {/* Known Exclusions */}
              <div>
                <label className={LABEL_CLS}>Known Exclusions / Clarifications</label>
                <textarea value={exclusions} onChange={(e) => setExclusions(e.target.value)} rows={2}
                  placeholder="e.g. Balustrades by others, ACP supplier nominated by client, glass is free-issue"
                  className={`${INPUT_CLS} resize-none`} />
              </div>

              {/* Free-text notes */}
              <div>
                <label className={LABEL_CLS}>Estimator Notes (free text)</label>
                <textarea value={estimatorNotes} onChange={(e) => setEstimatorNotes(e.target.value)} rows={4}
                  placeholder="Any additional context that helps produce an accurate estimate. For example:&#10;- Similar to Marina Tower project we did last year&#10;- Consultant is strict on thermal break profiles&#10;- Fast-track project, 8-week delivery expected&#10;- DWG has all floors overlapping in model space — typical layouts at levels 3-12&#10;- Retail glazing at ground floor is spider type with point-fixed fittings"
                  className={`${INPUT_CLS} resize-none`} />
              </div>
            </div>
          )}
        </div>

        {/* File Upload */}
        <div className="bg-white rounded-md border border-[#e2e8f0] p-5 shadow-sm">
          <div className="flex items-center gap-2 pb-3 border-b border-[#e2e8f0] mb-4">
            <Upload size={16} className="text-[#002147]" />
            <h3 className="text-sm font-semibold text-[#1e293b]">Upload Files</h3>
            <span className="text-xs text-[#64748b] ml-auto">At least one file required</span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {/* DWG */}
            <input ref={dwgRef} type="file" accept=".dwg,.dxf" className="hidden" onChange={(e) => setDwgFile(e.target.files?.[0] ?? null)} />
            <button type="button" onClick={() => dwgRef.current?.click()}
              className={`border-2 border-dashed rounded-md p-4 text-center transition-all hover:border-[#002147] ${dwgFile ? 'border-emerald-400 bg-emerald-50' : 'border-[#e2e8f0] hover:bg-blue-50/50'}`}>
              {dwgFile ? (
                <>
                  <CheckCircle2 size={20} className="mx-auto text-green-500 mb-1.5" />
                  <p className="text-xs font-semibold text-green-700 truncate">{dwgFile.name}</p>
                  <p className="text-[11px] text-green-500 mt-0.5">{(dwgFile.size / 1024 / 1024).toFixed(1)} MB</p>
                </>
              ) : (
                <>
                  <Upload size={20} className="mx-auto text-[#64748b] mb-1.5" />
                  <p className="text-xs font-semibold text-[#374151]">DWG / DXF</p>
                  <p className="text-[11px] text-[#64748b]">Drawing file</p>
                </>
              )}
            </button>

            {/* PDF Spec */}
            <input ref={specRef} type="file" accept=".pdf,.docx,.doc" className="hidden" onChange={(e) => setSpecFile(e.target.files?.[0] ?? null)} />
            <button type="button" onClick={() => specRef.current?.click()}
              className={`border-2 border-dashed rounded-md p-4 text-center transition-all hover:border-[#002147] ${specFile ? 'border-[#3b82f6] bg-blue-50' : 'border-[#e2e8f0] hover:bg-blue-50/50'}`}>
              {specFile ? (
                <>
                  <CheckCircle2 size={20} className="mx-auto text-blue-500 mb-1.5" />
                  <p className="text-xs font-semibold text-blue-700 truncate">{specFile.name}</p>
                  <p className="text-[11px] text-blue-500 mt-0.5">{(specFile.size / 1024 / 1024).toFixed(1)} MB</p>
                </>
              ) : (
                <>
                  <FileText size={20} className="mx-auto text-[#64748b] mb-1.5" />
                  <p className="text-xs font-semibold text-[#374151]">PDF / DOCX</p>
                  <p className="text-[11px] text-[#64748b]">Specification</p>
                </>
              )}
            </button>

            {/* Extra file */}
            <input ref={extraRef} type="file" className="hidden" onChange={(e) => setExtraFile(e.target.files?.[0] ?? null)} />
            <button type="button" onClick={() => extraRef.current?.click()}
              className={`border-2 border-dashed rounded-md p-4 text-center transition-all hover:border-[#002147] ${extraFile ? 'border-amber-400 bg-amber-50' : 'border-[#e2e8f0] hover:bg-blue-50/50'}`}>
              {extraFile ? (
                <>
                  <CheckCircle2 size={20} className="mx-auto text-amber-500 mb-1.5" />
                  <p className="text-xs font-semibold text-amber-700 truncate">{extraFile.name}</p>
                  <p className="text-[11px] text-amber-500 mt-0.5">{(extraFile.size / 1024 / 1024).toFixed(1)} MB</p>
                </>
              ) : (
                <>
                  <FileWarning size={20} className="mx-auto text-[#64748b] mb-1.5" />
                  <p className="text-xs font-semibold text-[#374151]">Extra File</p>
                  <p className="text-[11px] text-[#64748b]">BOQ, photos, etc.</p>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
            <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit */}
        <button onClick={handleSubmit} disabled={isProcessing}
          className="w-full flex items-center justify-center gap-3 bg-[#002147] hover:bg-[#1e3a5f] disabled:bg-slate-300 text-white py-3 rounded-md font-semibold text-sm transition-all">
          {isProcessing ? (
            <><Loader2 size={16} className="animate-spin" /> Submitting...</>
          ) : (
            <><Play size={16} /> Start Estimation</>
          )}
        </button>
      </div>
    </div>
  );
};

export default ProjectIngestion;
