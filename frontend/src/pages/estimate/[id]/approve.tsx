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
  ESTIMATING: 'bg-blue-50 text-blue-700 border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-green-50 text-green-700 border-green-200',
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
      const data = await apiGet<EstimateData>(`/api/ingestion/estimate/${id}`);
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
      await apiPost('/api/ingestion/approve', { estimate_id: id });
      setSuccess('Estimate approved successfully. Report generation will begin shortly.');
      await fetchEstimate();
    } catch (e: any) {
      setError(e.message || 'Approval failed');
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="animate-spin text-slate-400" size={28} />
      </div>
    );
  }

  if (error && !estimate) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-4">
          <AlertTriangle size={40} className="mx-auto text-red-400" />
          <p className="text-slate-700 font-semibold">Failed to load estimate</p>
          <p className="text-xs text-red-500 max-w-md">{error}</p>
          <Link href={`/estimate/${id}`} className="text-sm text-blue-600 hover:underline">
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
  const statusStyle = STATUS_STYLES[estimate.status] || 'bg-slate-50 text-slate-600 border-slate-200';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <Link href={`/estimate/${id}`} className="p-1.5 hover:bg-slate-100 rounded-md transition-colors">
          <ArrowLeft size={18} className="text-slate-400" />
        </Link>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <ShieldAlert size={20} className="text-amber-500" />
            Approval Gateway
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {estimate.project_name || `Estimate ${(estimate.estimate_id || '').slice(0, 8)}`}
          </p>
        </div>
        <span className={`px-2.5 py-0.5 text-[11px] font-semibold rounded border ${statusStyle}`}>
          {estimate.status.replace(/_/g, ' ')}
        </span>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm flex items-center gap-2">
          <AlertTriangle size={16} /> {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md text-green-700 text-sm flex items-center gap-2">
          <CheckCircle size={16} /> {success}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
            <DollarSign size={12} /> Contract Value
          </div>
          <p className="text-lg font-semibold text-slate-800 font-mono">
            AED {totalAED.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
            <ClipboardList size={12} /> BOM Items
          </div>
          <p className="text-lg font-semibold text-slate-800">{bomItemCount}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
            <BarChart3 size={12} /> Progress
          </div>
          <p className="text-lg font-semibold text-slate-800">{estimate.progress_pct}%</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
            <Zap size={12} /> VE Savings
          </div>
          <p className="text-lg font-semibold text-green-600 font-mono">
            AED {veTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>

      {/* Financial breakdown */}
      {estimate.financial_summary && Object.keys(estimate.financial_summary).length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2 text-sm">
            <BarChart3 size={16} className="text-blue-600" />
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
              <div key={label as string} className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">{label as string}</span>
                <span className="font-mono text-slate-800">
                  {typeof value === 'number'
                    ? `AED ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                    : value}
                </span>
              </div>
            ))}
            <div className="flex justify-between pt-3 font-semibold">
              <span className="text-slate-800">Total Contract Value</span>
              <span className="font-mono text-slate-900">
                AED {totalAED.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Approval action */}
      <div className="bg-white border border-slate-200 rounded-lg p-6">
        <h2 className="font-semibold text-slate-800 mb-3 flex items-center gap-2 text-sm">
          <CheckCircle size={16} className="text-green-600" />
          Final Sign-Off
        </h2>

        {isApproved ? (
          <div className="flex items-center gap-3 text-green-600 py-2">
            <CheckCircle size={22} />
            <div>
              <p className="font-semibold">Estimate Approved</p>
              <p className="text-sm text-slate-500">Report generation has been initiated.</p>
            </div>
          </div>
        ) : canApprove ? (
          <div>
            <p className="text-slate-500 text-sm mb-4">
              By approving this estimate, you confirm that all BOM items, pricing, compliance checks,
              and VE decisions have been reviewed. Report generation will begin immediately after approval.
            </p>
            <button
              onClick={handleApprove}
              disabled={approving}
              className="flex items-center gap-2 px-5 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-md font-medium text-sm transition-colors disabled:opacity-50"
            >
              {approving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
              {approving ? 'Processing...' : 'Approve and Generate Reports'}
            </button>
          </div>
        ) : (
          <p className="text-slate-500 text-sm">
            Estimate is in <strong>{estimate.status.replace(/_/g, ' ')}</strong> status. Approval is not available in this state.
          </p>
        )}
      </div>

      {/* Nav links */}
      <div className="flex gap-3 flex-wrap">
        <Link
          href={`/estimate/${id}`}
          className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 rounded-md text-sm text-slate-700 transition-colors"
        >
          Back to Estimate
        </Link>
        <Link
          href={`/estimate/${id}/compliance`}
          className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 rounded-md text-sm text-slate-700 transition-colors"
        >
          Compliance Report
        </Link>
        <Link
          href={`/estimate/${id}/ve-menu`}
          className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 rounded-md text-sm text-slate-700 transition-colors"
        >
          VE Menu
        </Link>
      </div>
    </div>
  );
}
