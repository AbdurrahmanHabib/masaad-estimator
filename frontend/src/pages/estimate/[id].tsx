import React, { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Layers,
  DollarSign,
  ShieldAlert,
  TrendingUp,
  Briefcase,
  MapPin,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ChevronRight,
  Download,
  Printer,
  Loader2,
  ArrowLeft,
  Package,
  ClipboardList,
  BarChart3,
  ShieldCheck,
  ListChecks,
} from 'lucide-react';
import { apiGet, apiPost, apiFetch } from '../../lib/api';

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

interface BOMItem {
  item_code?: string;
  description?: string;
  category?: string;
  quantity?: number;
  unit?: string;
  unit_rate?: number;
  subtotal_aed?: number;
  notes?: string;
}

interface FinancialSummary {
  total_aed?: number;
  material_cost_aed?: number;
  labor_cost_aed?: number;
  gross_margin_pct?: number;
  overhead_aed?: number;
  margin_aed?: number;
  attic_stock_cost_aed?: number;
  provisional_sums_aed?: number;
  retention_pct?: number;
  [key: string]: unknown;
}

interface EstimateDetail {
  estimate_id: string;
  project_id?: string;
  project_name?: string;
  client_name?: string;
  location?: string;
  status: string;
  progress_pct: number;
  current_step?: string;
  reasoning_log: string[];
  project_scope: Record<string, unknown>;
  opening_schedule: Record<string, unknown>;
  bom_output: {
    items?: BOMItem[];
  };
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
  financial_summary: FinancialSummary;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  ESTIMATING: 'bg-blue-50 text-blue-700 border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-green-50 text-green-700 border-green-200',
  DISPATCHED: 'bg-purple-50 text-purple-700 border-purple-200',
  Queued: 'bg-slate-50 text-slate-600 border-slate-200',
  Processing: 'bg-blue-50 text-blue-700 border-blue-200',
  Complete: 'bg-green-50 text-green-700 border-green-200',
  Error: 'bg-red-50 text-red-700 border-red-200',
};

function isDone(status: string) {
  return ['APPROVED', 'DISPATCHED', 'Complete', 'REVIEW_REQUIRED'].includes(status);
}

function fmtAED(value: number | undefined | null): string {
  if (value === undefined || value === null) return 'TBD';
  return `AED ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtNum(value: number | undefined | null, decimals = 2): string {
  if (value === undefined || value === null) return 'TBD';
  return value.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

type TabKey = 'summary' | 'bom' | 'scope' | 'financial' | 'compliance';

// ─── Progress Screen ──────────────────────────────────────────────────────────

function ProgressScreen({ progress, message }: { progress: number; message: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-slate-50 p-20">
      <div className="w-full max-w-md space-y-6 bg-white p-8 rounded-lg shadow-sm border border-slate-200">
        <div className="flex justify-between items-end mb-2">
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wider">Processing</span>
            <h3 className="text-sm font-medium text-slate-700 mt-1 max-w-xs truncate">{message || 'Initializing...'}</h3>
          </div>
          <span className="text-lg font-mono font-bold text-blue-600">{progress}%</span>
        </div>
        <div className="h-2 bg-slate-100 w-full rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-600 transition-all duration-700 rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex items-center gap-2 text-slate-400">
          <Loader2 size={14} className="animate-spin" />
          <p className="text-xs font-medium">Extracting geometry and specifications...</p>
        </div>
      </div>
    </div>
  );
}

// ─── HITL Banner ──────────────────────────────────────────────────────────────

function HITLBanner({ triageId }: { triageId: string }) {
  return (
    <div className="mx-4 mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between">
      <div className="flex items-center gap-3">
        <AlertTriangle size={16} className="text-amber-600" />
        <div>
          <p className="text-sm font-semibold text-amber-800">Human Review Required</p>
          <p className="text-xs text-amber-600">AI confidence below threshold -- triage item #{triageId.slice(0, 8)}</p>
        </div>
      </div>
      <Link
        href="/triage"
        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-md text-xs font-semibold transition-colors"
      >
        Review Now
      </Link>
    </div>
  );
}

// ─── BOM Table ────────────────────────────────────────────────────────────────

function BOMTable({ items }: { items: BOMItem[] }) {
  if (!items || items.length === 0) {
    return <div className="text-center text-slate-400 py-16 text-sm">No BOM items generated yet.</div>;
  }

  const totalAED = items.reduce((sum, item) => sum + (item.subtotal_aed || 0), 0);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="text-left py-3 px-4 font-semibold text-slate-600 text-xs w-12">#</th>
            <th className="text-left py-3 px-4 font-semibold text-slate-600 text-xs">Item Code</th>
            <th className="text-left py-3 px-4 font-semibold text-slate-600 text-xs">Description</th>
            <th className="text-left py-3 px-4 font-semibold text-slate-600 text-xs">Category</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-600 text-xs">Qty</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-600 text-xs">Unit</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-600 text-xs">Rate (AED)</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-600 text-xs">Total (AED)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item, i) => (
            <tr key={i} className="hover:bg-slate-50/50 transition-colors">
              <td className="py-3 px-4 text-slate-400 text-xs">{i + 1}</td>
              <td className="py-3 px-4 text-slate-700 font-mono text-xs">{item.item_code || '--'}</td>
              <td className="py-3 px-4 text-slate-800">{item.description || '--'}</td>
              <td className="py-3 px-4">
                {item.category ? (
                  <span className="inline-block px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs">
                    {item.category}
                  </span>
                ) : '--'}
              </td>
              <td className="py-3 px-4 text-right font-mono text-slate-700">
                {fmtNum(item.quantity)}
              </td>
              <td className="py-3 px-4 text-right text-slate-500 text-xs">{item.unit || '--'}</td>
              <td className="py-3 px-4 text-right font-mono text-slate-700">
                {item.unit_rate?.toFixed(2) || 'TBD'}
              </td>
              <td className="py-3 px-4 text-right font-mono font-semibold text-slate-800">
                {item.subtotal_aed?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'TBD'}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-slate-50 border-t-2 border-slate-200">
            <td colSpan={7} className="py-3 px-4 text-right font-semibold text-slate-700 text-sm">
              BOM Total
            </td>
            <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 text-sm">
              {fmtAED(totalAED)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

// ─── Scope Tab ────────────────────────────────────────────────────────────────

function ScopeTab({ scope, openings }: { scope: Record<string, unknown>; openings: Record<string, unknown> }) {
  const scopeEntries = Object.entries(scope || {});
  const openingEntries = Object.entries(openings || {});

  if (scopeEntries.length === 0 && openingEntries.length === 0) {
    return <div className="text-center text-slate-400 py-16 text-sm">No scope data available.</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {scopeEntries.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Project Scope</h3>
          <div className="bg-slate-50 rounded-md border border-slate-200 p-4">
            <pre className="text-xs text-slate-600 whitespace-pre-wrap font-mono">
              {JSON.stringify(scope, null, 2)}
            </pre>
          </div>
        </div>
      )}
      {openingEntries.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Opening Schedule</h3>
          <div className="bg-slate-50 rounded-md border border-slate-200 p-4">
            <pre className="text-xs text-slate-600 whitespace-pre-wrap font-mono">
              {JSON.stringify(openings, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Financial Tab ────────────────────────────────────────────────────────────

function FinancialTab({ financial, boqSummary }: { financial: FinancialSummary; boqSummary?: EstimateDetail['boq']['summary'] }) {
  const rows: [string, string][] = [];

  if (financial.material_cost_aed !== undefined) rows.push(['Material Cost', fmtAED(financial.material_cost_aed)]);
  if (financial.labor_cost_aed !== undefined) rows.push(['Labor Cost', fmtAED(financial.labor_cost_aed)]);
  if (financial.overhead_aed !== undefined) rows.push(['Overhead', fmtAED(financial.overhead_aed)]);
  if (financial.attic_stock_cost_aed !== undefined) rows.push(['Attic Stock (2%)', fmtAED(financial.attic_stock_cost_aed)]);
  if (financial.provisional_sums_aed !== undefined) rows.push(['Provisional Sums', fmtAED(financial.provisional_sums_aed)]);
  if (financial.margin_aed !== undefined) rows.push(['Margin', fmtAED(financial.margin_aed)]);
  if (financial.gross_margin_pct !== undefined) rows.push(['Gross Margin', `${(financial.gross_margin_pct * 100).toFixed(1)}%`]);

  if (boqSummary?.total_direct_cost_aed !== undefined) rows.push(['Total Direct Cost', fmtAED(boqSummary.total_direct_cost_aed)]);
  if (boqSummary?.total_weight_kg !== undefined) rows.push(['Total Weight', `${fmtNum(boqSummary.total_weight_kg, 1)} kg`]);

  const totalAED = financial.total_aed ?? boqSummary?.total_sell_price_aed;

  if (rows.length === 0 && totalAED === undefined) {
    return <div className="text-center text-slate-400 py-16 text-sm">No financial data available.</div>;
  }

  return (
    <div className="p-6">
      <div className="max-w-xl">
        <h3 className="text-sm font-semibold text-slate-700 mb-4">Financial Breakdown</h3>
        <div className="divide-y divide-slate-100">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between py-3 text-sm">
              <span className="text-slate-500">{label}</span>
              <span className="font-mono text-slate-800">{value}</span>
            </div>
          ))}
        </div>
        {totalAED !== undefined && (
          <div className="flex justify-between py-4 mt-2 border-t-2 border-slate-300">
            <span className="font-semibold text-slate-800">Total Contract Value</span>
            <span className="font-mono font-bold text-lg text-slate-900">{fmtAED(totalAED)}</span>
          </div>
        )}
        {financial.retention_pct !== undefined && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-700">
            Note: {financial.retention_pct}% retention locked for 12 months (not included in cashflow).
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Compliance Tab (inline summary) ─────────────────────────────────────────

function ComplianceTab({ structural, id }: { structural: EstimateDetail['structural_results']; id: string }) {
  if (!structural || structural.length === 0) {
    return (
      <div className="text-center text-slate-400 py-16 text-sm">
        <p>No compliance data available.</p>
        <Link href={`/estimate/${id}/compliance`} className="text-blue-600 hover:underline text-xs mt-2 inline-block">
          View full compliance report
        </Link>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700">Structural Check Summary</h3>
        <Link href={`/estimate/${id}/compliance`} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
          Full Report <ChevronRight size={12} />
        </Link>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="text-left py-2 px-4 font-semibold text-slate-600 text-xs">System Type</th>
            <th className="text-right py-2 px-4 font-semibold text-slate-600 text-xs">Deflection (mm)</th>
            <th className="text-center py-2 px-4 font-semibold text-slate-600 text-xs">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {structural.map((s, i) => (
            <tr key={i} className="hover:bg-slate-50/50">
              <td className="py-2 px-4 text-slate-700">{s.system_type || `System ${i + 1}`}</td>
              <td className="py-2 px-4 text-right font-mono text-slate-600">{s.deflection_mm?.toFixed(2) ?? '--'}</td>
              <td className="py-2 px-4 text-center">
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${s.pass ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                  {s.pass ? 'PASS' : 'FAIL'}
                </span>
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
  const [activeTab, setActiveTab] = useState<TabKey>('summary');
  const [downloading, setDownloading] = useState(false);
  const sseRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { setMounted(true); }, []);

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

  // SSE + polling
  useEffect(() => {
    if (!mounted || !id) return;
    const estimateId = id as string;

    const startSSE = () => {
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
        } catch { /* ignore parse errors */ }
      };

      es.onerror = () => {
        es.close();
        startPolling(estimateId);
      };
    };

    const startPolling = (eid: string) => {
      if (pollRef.current) return;
      pollRef.current = setInterval(async () => {
        try {
          const status = await apiGet<{
            estimate_id: string;
            status: string;
            progress_pct: number;
            current_step: string;
          }>(`/api/ingestion/status/${eid}`);

          setProgress(prev => ({
            ...(prev || { estimate_id: eid, current_agent: '', confidence_score: 1, partial_results: {} }),
            status_message: status.current_step || status.status,
            progress_pct: status.progress_pct || 0,
            partial_results: { status: status.status },
          }));

          if (isDone(status.status)) {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            fetchEstimate(eid);
          }
        } catch { /* ignore */ }
      }, 3000);
    };

    fetchEstimate(estimateId).then((data) => {
      if (data && isDone(data.status)) return;
      startSSE();
    });

    return () => {
      sseRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [mounted, id]);

  const handleDownloadPDF = async () => {
    if (!id) return;
    setDownloading(true);
    try {
      const response = await apiFetch(`/api/reports/estimate/${id}/pdf`, { method: 'GET' });
      if (!response.ok) throw new Error('PDF generation failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `estimate-${(id as string).slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Failed to download PDF: ${e}`);
    } finally {
      setDownloading(false);
    }
  };

  const handlePrint = () => { window.print(); };

  if (!mounted) return <div className="min-h-screen bg-slate-50" />;

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertTriangle size={40} className="mx-auto text-red-400" />
          <p className="text-slate-700 font-semibold">Failed to load estimate</p>
          <p className="text-xs text-red-500 max-w-md">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const currentStatus = estimate?.status || progress?.partial_results?.status || '';
  const showProgress = !estimate || !isDone(currentStatus);

  if (showProgress) {
    const pct = progress?.progress_pct ?? estimate?.progress_pct ?? 0;
    const msg = progress?.status_message ?? estimate?.current_step ?? 'Initializing...';

    if (progress?.hitl_required && progress.hitl_triage_id) {
      return (
        <div className="flex-1 flex flex-col">
          <HITLBanner triageId={progress.hitl_triage_id} />
          <ProgressScreen progress={pct} message={msg} />
        </div>
      );
    }

    return <ProgressScreen progress={pct} message={msg} />;
  }

  // ─── Data extraction ──────────────────────────────────────────────────────

  const bomItems: BOMItem[] = estimate.bom_output?.items ?? [];
  const boqItems = estimate.boq?.line_items ?? [];
  const boqSummary = estimate.boq?.summary;
  const financialRates = estimate.boq?.financial_rates;
  const financial = estimate.financial_summary || {};
  const rfiCount = estimate.rfi_register?.length ?? 0;
  const veTotal = estimate.ve_opportunities?.reduce((s, v) => s + (v.saving_aed || 0), 0) ?? 0;

  // Use BOM items if available, fall back to BOQ line items
  const displayBomItems: BOMItem[] = bomItems.length > 0
    ? bomItems
    : boqItems.map(item => ({
        item_code: item.item_code,
        description: item.description,
        category: item.system_type,
        quantity: item.quantity,
        unit: item.unit,
        unit_rate: item.unit_rate_aed,
        subtotal_aed: item.total_aed,
      }));

  const totalContractValue = financial.total_aed ?? boqSummary?.total_sell_price_aed;

  const TABS: { key: TabKey; label: string; icon: React.ElementType; count?: number }[] = [
    { key: 'summary', label: 'Summary', icon: ClipboardList },
    { key: 'bom', label: 'BOM', icon: Package, count: displayBomItems.length },
    { key: 'scope', label: 'Scope', icon: ListChecks },
    { key: 'financial', label: 'Financial', icon: BarChart3 },
    { key: 'compliance', label: 'Compliance', icon: ShieldCheck },
  ];

  return (
    <div className="flex flex-col gap-0 print:gap-0">

      {/* ── PROJECT HEADER ──────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 print:mb-4">
        <div className="flex items-start gap-4">
          <button onClick={() => router.push('/')} className="mt-1 p-1.5 hover:bg-slate-100 rounded-md transition-colors print:hidden">
            <ArrowLeft size={18} className="text-slate-400" />
          </button>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-xl font-bold text-slate-800">
                {estimate.project_name || `Estimate #${(estimate.estimate_id || '').slice(0, 8)}`}
              </h1>
              <span className={`px-2.5 py-0.5 text-[11px] font-semibold rounded border ${STATUS_STYLES[currentStatus] || STATUS_STYLES['Queued']}`}>
                {currentStatus.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
              {estimate.client_name && (
                <>
                  <span className="flex items-center gap-1"><Briefcase size={12} /> {estimate.client_name}</span>
                  <span className="w-1 h-1 bg-slate-300 rounded-full" />
                </>
              )}
              <span className="flex items-center gap-1"><MapPin size={12} /> {estimate.location || 'UAE'}</span>
              <span className="w-1 h-1 bg-slate-300 rounded-full" />
              <span className="flex items-center gap-1"><Clock size={12} /> ID: {(estimate.estimate_id || '').slice(0, 12)}</span>
              {financialRates?.lme_aluminum_usd_mt && (
                <>
                  <span className="w-1 h-1 bg-slate-300 rounded-full" />
                  <span className="font-mono text-slate-600">LME: ${financialRates.lme_aluminum_usd_mt.toFixed(0)}/MT</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 print:hidden">
          <button
            onClick={handleDownloadPDF}
            disabled={downloading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>
          <button
            onClick={handlePrint}
            className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-md text-xs font-medium transition-colors flex items-center gap-2"
          >
            <Printer size={14} /> Print
          </button>
          {currentStatus === 'REVIEW_REQUIRED' && (
            <Link
              href={`/estimate/${id}/approve`}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-md text-xs font-medium transition-colors flex items-center gap-2"
            >
              <ShieldAlert size={14} /> Approve
            </Link>
          )}
        </div>
      </div>

      {/* ── METRICS ROW ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6 print:grid-cols-4">
        {[
          {
            label: 'Contract Value',
            value: totalContractValue ? fmtAED(totalContractValue) : '--',
            icon: DollarSign,
            iconColor: 'text-blue-600',
          },
          {
            label: 'Gross Margin',
            value: (financial.gross_margin_pct ?? boqSummary?.gross_margin_pct)
              ? `${((financial.gross_margin_pct ?? boqSummary?.gross_margin_pct ?? 0) * 100).toFixed(1)}%`
              : '--',
            icon: TrendingUp,
            iconColor: 'text-green-600',
          },
          {
            label: 'BOM Items',
            value: String(displayBomItems.length),
            icon: Layers,
            iconColor: 'text-slate-600',
          },
          {
            label: 'Open RFIs',
            value: String(rfiCount),
            icon: FileText,
            iconColor: 'text-amber-600',
          },
        ].map((m) => (
          <div key={m.label} className="bg-white rounded-lg border border-slate-200 p-4 flex items-center gap-3">
            <m.icon size={18} className={m.iconColor} />
            <div>
              <div className="text-[11px] text-slate-500">{m.label}</div>
              <div className="text-base font-semibold text-slate-800 font-mono">{m.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ── TABS ─────────────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-lg border border-slate-200 flex-1 print:border-0 print:shadow-none">
        {/* Tab bar */}
        <div className="flex border-b border-slate-200 px-4 overflow-x-auto print:hidden">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              <tab.icon size={15} />
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="text-[11px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded-full font-mono">{tab.count}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="min-h-[400px]">
          {/* SUMMARY TAB */}
          {activeTab === 'summary' && (
            <div className="p-6 space-y-6">
              {/* Quick links */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Compliance Report', href: `/estimate/${id}/compliance`, icon: CheckCircle2 },
                  { label: 'RFI Log', href: `/estimate/${id}/rfi`, icon: FileText, badge: rfiCount > 0 ? rfiCount : undefined },
                  { label: 'VE Menu', href: `/estimate/${id}/ve-menu`, icon: TrendingUp, badge: veTotal > 0 ? `AED ${(veTotal / 1000).toFixed(0)}k` : undefined },
                  { label: 'Approval', href: `/estimate/${id}/approve`, icon: ShieldAlert },
                ].map((a) => (
                  <Link
                    key={a.href}
                    href={a.href}
                    className="flex items-center gap-3 p-3 rounded-md border border-slate-200 hover:bg-slate-50 hover:border-slate-300 transition-colors text-sm text-slate-700"
                  >
                    <a.icon size={16} className="text-slate-400 shrink-0" />
                    <span className="flex-1">{a.label}</span>
                    {a.badge !== undefined && (
                      <span className="text-xs bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200">{a.badge}</span>
                    )}
                    <ChevronRight size={14} className="text-slate-300" />
                  </Link>
                ))}
              </div>

              {/* Reasoning log */}
              <div>
                <h3 className="text-sm font-semibold text-slate-700 mb-3">Reasoning Log</h3>
                {estimate.reasoning_log.length === 0 ? (
                  <p className="text-sm text-slate-400">No log entries.</p>
                ) : (
                  <div className="bg-slate-50 rounded-md border border-slate-200 p-4 max-h-80 overflow-y-auto">
                    {estimate.reasoning_log.map((entry, i) => (
                      <div key={i} className="text-xs text-slate-600 py-1.5 border-b border-slate-100 last:border-0 font-mono">
                        <span className="text-slate-400 mr-3 select-none">{String(i + 1).padStart(3, '0')}</span>
                        {entry}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* VE Opportunities summary */}
              {estimate.ve_opportunities.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-700">VE Opportunities</h3>
                    <span className="text-xs font-mono text-green-600">Potential: {fmtAED(veTotal)}</span>
                  </div>
                  <div className="space-y-2">
                    {estimate.ve_opportunities.slice(0, 5).map((ve, i) => (
                      <div key={i} className="flex items-center justify-between text-sm p-2 bg-slate-50 rounded border border-slate-100">
                        <span className="text-slate-600 truncate flex-1">{ve.description || ve.item_code}</span>
                        <span className="font-mono text-green-600 text-xs ml-4 shrink-0">
                          -{(ve.saving_aed || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} AED
                        </span>
                      </div>
                    ))}
                    {estimate.ve_opportunities.length > 5 && (
                      <Link href={`/estimate/${id}/ve-menu`} className="text-xs text-blue-600 hover:underline">
                        +{estimate.ve_opportunities.length - 5} more opportunities
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* BOM TAB */}
          {activeTab === 'bom' && <BOMTable items={displayBomItems} />}

          {/* SCOPE TAB */}
          {activeTab === 'scope' && <ScopeTab scope={estimate.project_scope} openings={estimate.opening_schedule} />}

          {/* FINANCIAL TAB */}
          {activeTab === 'financial' && <FinancialTab financial={financial} boqSummary={boqSummary} />}

          {/* COMPLIANCE TAB */}
          {activeTab === 'compliance' && <ComplianceTab structural={estimate.structural_results} id={id as string} />}
        </div>
      </div>

      {/* ── FINANCIAL SUMMARY FOOTER ──────────────────────────────────────── */}
      {totalContractValue !== undefined && (
        <div className="mt-4 bg-white rounded-lg border border-slate-200 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 print:mt-2">
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-slate-500">Material</span>
              <span className="ml-2 font-mono font-medium text-slate-800">{fmtAED(financial.material_cost_aed)}</span>
            </div>
            <div>
              <span className="text-slate-500">Labor</span>
              <span className="ml-2 font-mono font-medium text-slate-800">{fmtAED(financial.labor_cost_aed)}</span>
            </div>
            {financial.gross_margin_pct !== undefined && (
              <div>
                <span className="text-slate-500">Margin</span>
                <span className="ml-2 font-mono font-medium text-slate-800">{(financial.gross_margin_pct * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-500 mr-3">Total Contract Value</span>
            <span className="text-lg font-bold font-mono text-slate-900">{fmtAED(totalContractValue)}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default EstimatePage;
