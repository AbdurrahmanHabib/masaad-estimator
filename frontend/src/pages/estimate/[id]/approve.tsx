/**
 * Approval Gateway -- Admin-only final sign-off before report generation.
 * State machine: REVIEW_REQUIRED -> APPROVED -> DISPATCHED
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  CheckCircle, Loader2, ShieldAlert, DollarSign,
  BarChart3, ClipboardList, Zap, ArrowLeft, AlertTriangle
} from 'lucide-react';
import { apiGet, apiPost } from '../../../lib/api';

interface EstimateData {
  estimate_id: string;
  project_name?: string;
  location?: string;
  status: string;
  progress_pct: number;
  bom_output?: {
    items?: unknown[];
  };
  financial_summary?: {
    total_aed?: number;
    material_cost_aed?: number;
    labor_cost_aed?: number;
    gross_margin_pct?: number;
  };
  boq?: {
    summary?: {
      total_sell_price_aed?: number;
    };
    line_items?: unknown[];
  };
  ve_opportunities?: Array<{ saving_aed?: number }>;
}

const STATUS_STYLES: Record<string, string> = {
  ESTIMATING: 'bg-blue-50 text-[#002147] border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  DISPATCHED: 'bg-purple-50 text-purple-700 border-purple-200',
};

export default function ApprovePage() {
  const router = useRouter();
  const { id } = router.query;
  const [estimate, setEstimate] = useState<EstimateData | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchEstimate = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<EstimateData>(`/api/v1/estimates/${id}`);
      setEstimate(data);
    } catch (e: any) {
      setError(e.message || 'Failed to load estimate data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchEstimate(); }, [id]);

  const handleApprove = async () => {
    if (!id) return;
    setApproving(true);
    setError(null);
    try {
      await apiPost(`/api/v1/estimates/${id}/approve`, {});
      setSuccess('Estimate approved successfully. Redirecting to approved summary...');
      await fetchEstimate();
      // Redirect to estimate detail after short delay so user sees success message
      setTimeout(() => router.push(`/estimate/${id}`), 1500);
    } catch (e: any) {
      setError(e.message || 'Approval failed');
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="animate-spin text-[#64748b]" size={28} />
      </div>
    );
  }

  if (error && !estimate) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-4">
          <AlertTriangle size={40} className="mx-auto text-[#dc2626]" />
          <p className="text-[#1e293b] font-semibold">Failed to load estimate</p>
          <p className="text-xs text-[#dc2626] max-w-md">{error}</p>
          <Link href={`/estimate/${id}`} className="text-sm text-[#002147] hover:underline">
            Back to Estimate
          </Link>
        </div>
      </div>
    );
  }

  if (!estimate) return null;

  const totalAED = estimate.financial_summary?.total_aed ?? estimate.boq?.summary?.total_sell_price_aed ?? 0;
  const bomItemCount = estimate.bom_output?.items?.length ?? estimate.boq?.line_items?.length ?? 0;
  const veTotal = estimate.ve_opportunities?.reduce((s, v) => s + (v.saving_aed || 0), 0) ?? 0;
  const canApprove = estimate.status === 'REVIEW_REQUIRED';
  const isApproved = estimate.status === 'APPROVED' || estimate.status === 'DISPATCHED';
  const statusStyle = STATUS_STYLES[estimate.status] || 'bg-slate-50 text-[#64748b] border-slate-200';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <Link href={`/estimate/${id}`} className="p-1.5 hover:bg-slate-100 rounded-md transition-colors">
          <ArrowLeft size={18} className="text-[#64748b]" />
        </Link>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-[#002147] flex items-center gap-2">
            <ShieldAlert size={20} className="text-[#94a3b8]" />
            Approval Gateway
          </h1>
          <p className="text-xs text-[#64748b] mt-0.5">
            {estimate.project_name || `Estimate ${(estimate.estimate_id || '').slice(0, 8)}`}
          </p>
        </div>
        <span className={`px-2.5 py-0.5 text-[11px] font-semibold rounded-md border ${statusStyle}`}>
          {estimate.status.replace(/_/g, ' ')}
        </span>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-[#dc2626] text-sm flex items-center gap-2">
          <AlertTriangle size={16} /> {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-emerald-700 text-sm flex items-center gap-2">
          <CheckCircle size={16} /> {success}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-[#e2e8f0] rounded-md p-4">
          <div className="flex items-center gap-2 text-[#64748b] text-xs mb-1">
            <DollarSign size={12} /> Contract Value
          </div>
          <p className="text-lg font-semibold text-[#002147] font-mono">
            AED {totalAED.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-white border border-[#e2e8f0] rounded-md p-4">
          <div className="flex items-center gap-2 text-[#64748b] text-xs mb-1">
            <ClipboardList size={12} /> BOM Items
          </div>
          <p className="text-lg font-semibold text-[#1e293b]">{bomItemCount}</p>
        </div>
        <div className="bg-white border border-[#e2e8f0] rounded-md p-4">
          <div className="flex items-center gap-2 text-[#64748b] text-xs mb-1">
            <BarChart3 size={12} /> Progress
          </div>
          <p className="text-lg font-semibold text-[#1e293b]">{estimate.progress_pct}%</p>
        </div>
        <div className="bg-white border border-[#e2e8f0] rounded-md p-4">
          <div className="flex items-center gap-2 text-[#64748b] text-xs mb-1">
            <Zap size={12} /> VE Savings
          </div>
          <p className="text-lg font-semibold text-[#059669] font-mono">
            AED {veTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>

      {/* Financial breakdown */}
      {estimate.financial_summary && Object.keys(estimate.financial_summary).length > 0 && (
        <div className="bg-white border border-[#e2e8f0] rounded-md p-6">
          <h2 className="font-semibold text-[#002147] mb-4 flex items-center gap-2 text-sm">
            <BarChart3 size={16} className="text-[#002147]" />
            Financial Summary
          </h2>
          <div className="space-y-2 text-sm">
            {[
              ['Material Cost', estimate.financial_summary.material_cost_aed],
              ['Labor Cost', estimate.financial_summary.labor_cost_aed],
              ['Gross Margin', estimate.financial_summary.gross_margin_pct !== undefined
                ? `${(estimate.financial_summary.gross_margin_pct * 100).toFixed(1)}%`
                : undefined],
            ].filter(([, v]) => v !== undefined && v !== null).map(([label, value]) => (
              <div key={label as string} className="flex justify-between py-2 border-b border-[#e2e8f0]">
                <span className="text-[#64748b]">{label as string}</span>
                <span className="font-mono text-[#1e293b]">
                  {typeof value === 'number'
                    ? `AED ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : value}
                </span>
              </div>
            ))}
            <div className="flex justify-between pt-3 font-semibold">
              <span className="text-[#002147]">Total Contract Value</span>
              <span className="font-mono text-[#002147]">
                AED {totalAED.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Approval action */}
      <div className="bg-white border border-[#e2e8f0] rounded-md p-6">
        <h2 className="font-semibold text-[#002147] mb-3 flex items-center gap-2 text-sm">
          <CheckCircle size={16} className="text-[#059669]" />
          Final Sign-Off
        </h2>

        {isApproved ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-[#059669] py-2">
              <CheckCircle size={20} />
              <div>
                <p className="font-semibold">Estimate Approved</p>
                <p className="text-sm text-[#64748b]">Report generation has been initiated.</p>
              </div>
            </div>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/ingestion/download/${id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#002147] hover:bg-[#001a3a] text-white rounded-md font-semibold text-sm transition-colors"
            >
              <Zap size={16} />
              Download Final PDF Proposal
            </a>
          </div>
        ) : canApprove ? (
          <div>
            <p className="text-[#64748b] text-sm mb-4">
              By approving this estimate, you confirm that all BOM items, pricing, compliance checks,
              and VE decisions have been reviewed. Report generation will begin immediately after approval.
            </p>
            <button
              onClick={handleApprove}
              disabled={approving}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#002147] hover:bg-[#1e3a5f] text-white rounded-md font-semibold text-sm transition-colors disabled:opacity-50"
            >
              {approving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
              {approving ? 'Processing...' : 'Approve and Generate Reports'}
            </button>
          </div>
        ) : (
          <p className="text-[#64748b] text-sm">
            Estimate is in <strong>{estimate.status.replace(/_/g, ' ')}</strong> status. Approval is not available in this state.
          </p>
        )}
      </div>

      {/* Nav links */}
      <div className="flex gap-3 flex-wrap">
        <Link
          href={`/estimate/${id}`}
          className="px-4 py-2 bg-white border border-[#e2e8f0] hover:bg-slate-50 rounded-md text-sm text-[#1e293b] transition-colors"
        >
          Back to Estimate
        </Link>
        <Link
          href={`/estimate/${id}/compliance`}
          className="px-4 py-2 bg-white border border-[#e2e8f0] hover:bg-slate-50 rounded-md text-sm text-[#1e293b] transition-colors"
        >
          Compliance Report
        </Link>
        <Link
          href={`/estimate/${id}/ve-menu`}
          className="px-4 py-2 bg-white border border-[#e2e8f0] hover:bg-slate-50 rounded-md text-sm text-[#1e293b] transition-colors"
        >
          VE Menu
        </Link>
      </div>
    </div>
  );
}
