import React, { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Layers,
  Activity,
  DollarSign,
  ShieldAlert,
  BarChart3,
  TrendingUp,
  Briefcase,
  MapPin,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  GitBranch,
  Cpu,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { apiGet, apiPost } from '../../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface SSEProgress {
  estimate_id: string;
  current_agent: string;
  status_message: string;
  confidence_score: number;
  progress_pct: number;
  partial_results?: {
    status?: string;
    bom_rows?: number;
  };
  hitl_required?: boolean;
  hitl_triage_id?: string | null;
  error?: string | null;
}

interface EstimateDetail {
  estimate_id: string;
  project_id: string;
  status: string;
  progress_pct: number;
  current_step: string;
  reasoning_log: string[];
  project_scope: Record<string, unknown>;
  opening_schedule: Record<string, unknown>;
  bom_output: Record<string, unknown>;
  cutting_list: Record<string, unknown>;
  boq: {
    summary?: {
      total_sell_price_aed?: number;
      total_direct_cost_aed?: number;
      gross_margin_pct?: number;
      total_weight_kg?: number;
    };
    line_items?: Array<{
      system_type?: string;
      item_code?: string;
      description?: string;
      quantity?: number;
      unit?: string;
      unit_rate_aed?: number;
      total_aed?: number;
    }>;
    financial_rates?: {
      lme_aluminum_usd_mt?: number;
      usd_aed_rate?: number;
      baseline_labor_burn_rate_aed?: number;
    };
  };
  rfi_register: Array<{
    rfi_id?: string;
    rfi_code?: string;
    question?: string;
    status?: string;
  }>;
  ve_opportunities: Array<{
    item_code?: string;
    description?: string;
    saving_aed?: number;
  }>;
  structural_results: Array<{
    system_type?: string;
    pass?: boolean;
    deflection_mm?: number;
  }>;
  financial_summary: Record<string, unknown>;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  ESTIMATING: 'bg-blue-100 text-blue-700 border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-100 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  DISPATCHED: 'bg-purple-100 text-purple-700 border-purple-200',
  Queued: 'bg-slate-100 text-slate-600 border-slate-200',
  Processing: 'bg-blue-100 text-blue-700 border-blue-200',
  Complete: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  Error: 'bg-red-100 text-red-700 border-red-200',
};

function isDone(status: string) {
  return ['APPROVED', 'DISPATCHED', 'Complete', 'REVIEW_REQUIRED'].includes(status);
}

// ─── Progress Screen ──────────────────────────────────────────────────────────

function ProgressScreen({ progress, message, confidence }: { progress: number; message: string; confidence: number }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-slate-50 p-20">
      <div className="w-full max-w-lg space-y-6 bg-white p-10 rounded-2xl shadow-xl border border-slate-200">
        <div className="flex justify-between items-end mb-2">
          <div className="flex flex-col">
            <span className="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em]">Fusion_Engine_Active</span>
            <h3 className="text-sm font-bold text-slate-800 mt-1 max-w-xs truncate">{message || 'Processing…'}</h3>
          </div>
          <span className="text-xl font-mono font-black text-blue-600">{progress}%</span>
        </div>
        <div className="h-3 bg-slate-100 w-full rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-blue-700 transition-all duration-700 shadow-lg"
            style={{ width: `${progress}%` }}
          />
        </div>
        {confidence > 0 && (
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span className="font-semibold">AI Confidence:</span>
            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${confidence >= 0.9 ? 'bg-emerald-500' : confidence >= 0.7 ? 'bg-amber-500' : 'bg-red-500'}`}
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <span className="font-mono font-bold">{(confidence * 100).toFixed(0)}%</span>
          </div>
        )}
        <div className="flex items-center gap-2 text-slate-400">
          <Clock size={14} className="animate-spin" />
          <p className="text-[10px] font-medium uppercase tracking-widest">Extracting Geometry & Specs…</p>
        </div>
      </div>
    </div>
  );
}

// ─── HITL Banner ──────────────────────────────────────────────────────────────

function HITLBanner({ triageId }: { triageId: string }) {
  return (
    <div className="mx-6 mt-4 p-4 bg-amber-50 border border-amber-300 rounded-xl flex items-center justify-between">
      <div className="flex items-center gap-3">
        <AlertTriangle size={18} className="text-amber-600" />
        <div>
          <p className="text-sm font-bold text-amber-800">Human Review Required</p>
          <p className="text-xs text-amber-600">AI confidence below threshold — triage item #{triageId.slice(0, 8)}</p>
        </div>
      </div>
      <Link
        href="/triage"
        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold uppercase tracking-widest transition-all"
      >
        Review Now
      </Link>
    </div>
  );
}

// ─── BOQ Table ────────────────────────────────────────────────────────────────

function BOQTable({ items }: { items: EstimateDetail['boq']['line_items'] }) {
  if (!items || items.length === 0) {
    return <div className="text-center text-slate-400 py-12 text-sm">No BOQ items generated yet.</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="text-left py-3 px-4 font-bold text-slate-600 uppercase tracking-widest">Description</th>
            <th className="text-right py-3 px-4 font-bold text-slate-600 uppercase tracking-widest">Qty</th>
            <th className="text-right py-3 px-4 font-bold text-slate-600 uppercase tracking-widest">Unit</th>
            <th className="text-right py-3 px-4 font-bold text-slate-600 uppercase tracking-widest">Rate AED</th>
            <th className="text-right py-3 px-4 font-bold text-slate-600 uppercase tracking-widest">Total AED</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item, i) => (
            <tr key={i} className="hover:bg-slate-50 transition-colors">
              <td className="py-3 px-4 text-slate-800 font-medium">
                <div>{item.description || item.item_code || '—'}</div>
                {item.system_type && (
                  <div className="text-[10px] text-slate-400 mt-0.5 uppercase">{item.system_type}</div>
                )}
              </td>
              <td className="py-3 px-4 text-right font-mono text-slate-700">
                {item.quantity?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? '—'}
              </td>
              <td className="py-3 px-4 text-right text-slate-500">{item.unit || '—'}</td>
              <td className="py-3 px-4 text-right font-mono text-slate-700">
                {item.unit_rate_aed?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—'}
              </td>
              <td className="py-3 px-4 text-right font-mono font-bold text-slate-800">
                {item.total_aed?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

const EstimatePage = () => {
  const router = useRouter();
  const { id } = router.query;
  const [mounted, setMounted] = useState(false);
  const [progress, setProgress] = useState<SSEProgress | null>(null);
  const [estimate, setEstimate] = useState<EstimateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'boq' | 'rfi' | 'log'>('boq');
  const sseRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { setMounted(true); }, []);

  // Fetch full estimate detail
  const fetchEstimate = async (estimateId: string) => {
    try {
      const data = await apiGet<EstimateDetail>(`/api/ingestion/estimate/${estimateId}`);
      setEstimate(data);
      return data;
    } catch (e) {
      setError(String(e));
      return null;
    }
  };

  // Start SSE connection for live progress
  useEffect(() => {
    if (!mounted || !id) return;
    const estimateId = id as string;

    const startSSE = () => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
      const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/ingestion/progress/${estimateId}`;
      const es = new EventSource(url);
      sseRef.current = es;

      es.onmessage = (event) => {
        try {
          const payload: SSEProgress = JSON.parse(event.data);
          setProgress(payload);
          if (isDone(payload.partial_results?.status || '')) {
            es.close();
            fetchEstimate(estimateId);
          }
        } catch {}
      };

      es.onerror = () => {
        es.close();
        // Fallback: poll status endpoint
        startPolling(estimateId);
      };
    };

    const startPolling = (estimateId: string) => {
      if (pollRef.current) return; // already polling
      pollRef.current = setInterval(async () => {
        try {
          const status = await apiGet<{
            estimate_id: string;
            status: string;
            progress_pct: number;
            current_step: string;
          }>(`/api/ingestion/status/${estimateId}`);

          setProgress(prev => ({
            ...(prev || { estimate_id: estimateId, current_agent: '', confidence_score: 1, partial_results: {} }),
            status_message: status.current_step || status.status,
            progress_pct: status.progress_pct || 0,
            partial_results: { status: status.status },
          }));

          if (isDone(status.status)) {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            fetchEstimate(estimateId);
          }
        } catch {}
      }, 3000);
    };

    // Initial fetch to check if already done
    fetchEstimate(estimateId).then((data) => {
      if (data && isDone(data.status)) return; // already complete, no need for SSE
      startSSE();
    });

    return () => {
      sseRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [mounted, id]);

  if (!mounted) return <div className="min-h-screen bg-slate-50" />;

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertTriangle size={48} className="mx-auto text-red-400" />
          <p className="text-slate-600 font-semibold">Failed to load estimate</p>
          <p className="text-xs text-red-500">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Show progress screen if not done
  const currentStatus = estimate?.status || progress?.partial_results?.status || '';
  const showProgress = !estimate || !isDone(currentStatus);

  if (showProgress) {
    const pct = progress?.progress_pct ?? estimate?.progress_pct ?? 0;
    const msg = progress?.status_message ?? estimate?.current_step ?? 'Initializing…';
    const conf = progress?.confidence_score ?? 1;

    if (progress?.hitl_required && progress.hitl_triage_id) {
      return (
        <div className="flex-1 flex flex-col">
          <HITLBanner triageId={progress.hitl_triage_id} />
          <ProgressScreen progress={pct} message={msg} confidence={conf} />
        </div>
      );
    }

    return <ProgressScreen progress={pct} message={msg} confidence={conf} />;
  }

  const boqSummary = estimate.boq?.summary;
  const boqItems = estimate.boq?.line_items ?? [];
  const financialRates = estimate.boq?.financial_rates;
  const rfiCount = estimate.rfi_register?.length ?? 0;
  const veTotal = estimate.ve_opportunities?.reduce((s, v) => s + (v.saving_aed || 0), 0) ?? 0;

  return (
    <div className="flex flex-col h-full bg-slate-50 overflow-hidden gap-4 p-4">

      {/* ── TOP BAR ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
        <div className="flex items-center gap-5">
          <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600">
            <Briefcase size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-base font-black text-slate-800 uppercase tracking-tight">
                {(estimate as any)?.project_name || `Estimate #${(estimate.estimate_id || '').slice(0, 8)}`}
              </h1>
              <span className={`px-2 py-0.5 text-[9px] font-black uppercase tracking-widest rounded border ${STATUS_COLORS[currentStatus] || STATUS_COLORS['Queued']}`}>
                {currentStatus}
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1"><MapPin size={12} /> {(estimate as any)?.location || 'UAE'}</span>
              <span className="w-1 h-1 bg-slate-300 rounded-full" />
              <span className="flex items-center gap-1"><Clock size={12} /> Updated: {new Date().toLocaleDateString()}</span>
              {financialRates?.lme_aluminum_usd_mt && (
                <>
                  <span className="w-1 h-1 bg-slate-300 rounded-full" />
                  <span className="font-mono font-semibold text-blue-600">LME: ${financialRates.lme_aluminum_usd_mt.toFixed(0)}/MT</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          {currentStatus === 'REVIEW_REQUIRED' && (
            <Link
              href={`/estimate/${id}/approve`}
              className="px-5 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center gap-2"
            >
              <ShieldAlert size={14} /> Approve
            </Link>
          )}
          <Link
            href={`/estimate/${id}/compliance`}
            className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center gap-2"
          >
            <CheckCircle2 size={14} /> Compliance
          </Link>
          <Link
            href={`/estimate/${id}/rfi`}
            className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center gap-2"
          >
            <FileText size={14} /> RFI {rfiCount > 0 && <span className="bg-amber-500 text-white rounded-full text-[9px] w-4 h-4 flex items-center justify-center">{rfiCount}</span>}
          </Link>
          <Link
            href={`/estimate/${id}/ve-menu`}
            className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center gap-2"
          >
            <TrendingUp size={14} /> VE {veTotal > 0 && <span className="text-emerald-600 font-mono text-[10px]">AED {(veTotal / 1000).toFixed(0)}k</span>}
          </Link>
        </div>
      </div>

      {/* ── METRICS ROW ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-4">
        {[
          {
            label: 'Total Sell Price',
            value: boqSummary?.total_sell_price_aed
              ? `AED ${(boqSummary.total_sell_price_aed / 1000).toFixed(0)}k`
              : '—',
            icon: DollarSign,
            color: 'text-blue-600 bg-blue-50',
          },
          {
            label: 'Gross Margin',
            value: boqSummary?.gross_margin_pct
              ? `${(boqSummary.gross_margin_pct * 100).toFixed(1)}%`
              : '—',
            icon: TrendingUp,
            color: 'text-emerald-600 bg-emerald-50',
          },
          {
            label: 'Net Material Mass',
            value: boqSummary?.total_weight_kg
              ? `${(boqSummary.total_weight_kg / 1000).toFixed(1)}t`
              : '—',
            icon: Layers,
            color: 'text-slate-600 bg-slate-100',
          },
          {
            label: 'AI Confidence',
            value: progress?.confidence_score
              ? `${(progress.confidence_score * 100).toFixed(0)}%`
              : '100%',
            icon: Cpu,
            color: 'text-purple-600 bg-purple-50',
          },
        ].map((m) => (
          <div key={m.label} className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${m.color}`}>
              <m.icon size={20} />
            </div>
            <div>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{m.label}</div>
              <div className="text-xl font-mono font-black text-slate-800 mt-0.5">{m.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── MAIN CONTENT ────────────────────────────────────────────────────── */}
      <div className="flex flex-1 gap-4 overflow-hidden min-h-0">

        {/* LEFT — BOQ / RFI / Log tabs */}
        <div className="flex-1 bg-white rounded-2xl border border-slate-200 flex flex-col overflow-hidden">
          <div className="flex border-b border-slate-200 px-4 py-3 gap-2">
            {(['boq', 'rfi', 'log'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-[10px] font-bold uppercase tracking-widest rounded-lg transition-all ${
                  activeTab === tab ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab === 'boq' ? `BOQ (${boqItems.length})` : tab === 'rfi' ? `RFI (${rfiCount})` : 'Reasoning Log'}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto">
            {activeTab === 'boq' && <BOQTable items={boqItems} />}

            {activeTab === 'rfi' && (
              <div className="p-4 space-y-2">
                {estimate.rfi_register.length === 0 ? (
                  <div className="text-center text-slate-400 py-12 text-sm">No open RFIs.</div>
                ) : (
                  estimate.rfi_register.map((rfi, i) => (
                    <div key={i} className="p-3 border border-slate-100 rounded-xl bg-slate-50 flex items-start gap-3">
                      <AlertTriangle size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-slate-700">{rfi.rfi_code || `RFI-${i + 1}`}</div>
                        <div className="text-xs text-slate-500 mt-0.5 truncate">{rfi.question || '—'}</div>
                      </div>
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded border flex-shrink-0 ${rfi.status === 'open' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
                        {rfi.status || 'open'}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'log' && (
              <div className="p-4 space-y-1 font-mono text-[11px]">
                {estimate.reasoning_log.length === 0 ? (
                  <div className="text-center text-slate-400 py-12 text-sm font-sans">No log entries.</div>
                ) : (
                  estimate.reasoning_log.map((entry, i) => (
                    <div key={i} className="text-slate-600 py-1 border-b border-slate-50">
                      <span className="text-slate-400 mr-2">{String(i + 1).padStart(3, '0')}</span>
                      {entry}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="w-72 flex flex-col gap-4 overflow-y-auto">

          {/* Financial Rates */}
          {financialRates && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-4">
                <Activity size={16} className="text-blue-600" />
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700">Market Rates</h3>
              </div>
              <div className="space-y-3 text-xs">
                {[
                  ['LME Aluminium', `$${financialRates.lme_aluminum_usd_mt?.toFixed(0) ?? '—'}/MT`],
                  ['USD/AED', financialRates.usd_aed_rate?.toFixed(4) ?? '—'],
                  ['Labor Burn Rate', `AED ${financialRates.baseline_labor_burn_rate_aed?.toFixed(2) ?? '—'}/hr`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-mono font-bold text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VE Opportunities */}
          {estimate.ve_opportunities.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <TrendingUp size={16} className="text-emerald-600" />
                  <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700">VE Opportunities</h3>
                </div>
                <span className="text-[10px] font-mono font-bold text-emerald-600">
                  AED {veTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div className="space-y-2">
                {estimate.ve_opportunities.slice(0, 4).map((ve, i) => (
                  <div key={i} className="flex items-start justify-between gap-2 text-xs">
                    <span className="text-slate-600 flex-1 truncate">{ve.description || ve.item_code}</span>
                    <span className="font-mono font-bold text-emerald-600 flex-shrink-0">
                      -{(ve.saving_aed || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                ))}
                {estimate.ve_opportunities.length > 4 && (
                  <Link
                    href={`/estimate/${id}/ve-menu`}
                    className="text-[10px] text-blue-600 font-semibold flex items-center gap-1 pt-2 hover:underline"
                  >
                    +{estimate.ve_opportunities.length - 4} more <ChevronRight size={12} />
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* Structural */}
          {estimate.structural_results.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-4">
                <ShieldAlert size={16} className="text-slate-600" />
                <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700">Structural</h3>
              </div>
              <div className="space-y-2">
                {estimate.structural_results.slice(0, 3).map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-slate-600 truncate flex-1">{s.system_type || `System ${i + 1}`}</span>
                    <span className={`font-bold flex-shrink-0 ${s.pass ? 'text-emerald-600' : 'text-red-600'}`}>
                      {s.pass ? '✓ PASS' : '✗ FAIL'}
                    </span>
                  </div>
                ))}
              </div>
              <Link
                href={`/estimate/${id}/compliance`}
                className="mt-3 flex items-center gap-1 text-[10px] text-blue-600 font-semibold hover:underline"
              >
                Full Report <ExternalLink size={10} />
              </Link>
            </div>
          )}

          {/* Quick Actions */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-700 mb-3">Quick Actions</h3>
            <div className="space-y-2">
              {[
                { label: 'Compliance Report', href: `/estimate/${id}/compliance`, icon: CheckCircle2 },
                { label: 'RFI Log', href: `/estimate/${id}/rfi`, icon: FileText },
                { label: 'VE Menu', href: `/estimate/${id}/ve-menu`, icon: TrendingUp },
                { label: 'Approval Gateway', href: `/estimate/${id}/approve`, icon: GitBranch },
              ].map((a) => (
                <Link
                  key={a.href}
                  href={a.href}
                  className="flex items-center gap-2 p-2.5 rounded-lg border border-slate-100 hover:bg-slate-50 hover:border-slate-200 transition-all text-xs font-semibold text-slate-700"
                >
                  <a.icon size={14} className="text-blue-600" />
                  {a.label}
                  <ChevronRight size={12} className="ml-auto text-slate-400" />
                </Link>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default EstimatePage;
