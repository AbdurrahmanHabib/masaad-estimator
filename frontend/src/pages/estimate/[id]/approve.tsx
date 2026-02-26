/**
 * Approval Gateway — Admin-only final sign-off before report generation.
 * State machine: REVIEW_REQUIRED → APPROVED → DISPATCHED
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  CheckCircle, XCircle, Loader, ShieldAlert, DollarSign,
  FileText, BarChart3, ClipboardList, Zap
} from 'lucide-react';
import { apiGet, apiPost } from '../../../lib/api';

interface EstimateSummary {
  id: string;
  status: string;
  progress_pct: number;
  total_aed: number;
  bom_items_count: number;
  compliance_passed: boolean | null;
  ve_accepted_savings: number;
  approved_by: string | null;
  approved_at: string | null;
}

interface ApprovalInfo {
  estimate: EstimateSummary;
  state_snapshot: {
    pricing_data?: Record<string, any>;
    compliance_report?: Record<string, any>;
    ve_menu?: Record<string, any>;
    bom_items?: any[];
  };
}

const StatusPill = ({ status }: { status: string }) => {
  const colors: Record<string, string> = {
    ESTIMATING: 'bg-blue-900/30 text-blue-300 border-blue-700',
    REVIEW_REQUIRED: 'bg-amber-900/30 text-amber-300 border-amber-700',
    APPROVED: 'bg-green-900/30 text-green-300 border-green-700',
    DISPATCHED: 'bg-purple-900/30 text-purple-300 border-purple-700',
  };
  return (
    <span className={`px-3 py-1 rounded-full border text-sm font-medium ${colors[status] || 'bg-gray-700 text-gray-300 border-gray-600'}`}>
      {status.replace('_', ' ')}
    </span>
  );
};

export default function ApprovePage() {
  const router = useRouter();
  const { id } = router.query;
  const [info, setInfo] = useState<ApprovalInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchInfo = async () => {
    if (!id) return;
    setLoading(true);
    try {
      // Load estimate data from the estimates endpoint
      const est = await apiGet<any>(`/api/v1/estimates/${id}`);
      const snapshot = est.state_snapshot || {};
      const pricing = snapshot.pricing_data || {};
      const boqItems = snapshot.bom_items || [];
      const compReport = snapshot.compliance_report;
      const veMenu = snapshot.ve_menu;

      setInfo({
        estimate: {
          id: est.id,
          status: est.status,
          progress_pct: est.progress_pct || 0,
          total_aed: pricing.total_aed || 0,
          bom_items_count: boqItems.length,
          compliance_passed: compReport?.overall_passed ?? null,
          ve_accepted_savings: veMenu?.accepted_savings_aed || 0,
          approved_by: est.approved_by || null,
          approved_at: est.approved_at || null,
        },
        state_snapshot: snapshot,
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInfo(); }, [id]);

  const handleApprove = async () => {
    if (!id) return;
    setApproving(true);
    setError(null);
    try {
      await apiPost(`/api/v1/estimates/${id}/approve`, {});
      setSuccess('Estimate approved! Report generation will begin shortly.');
      await fetchInfo();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setApproving(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <Loader className="animate-spin text-blue-400" size={32} />
    </div>
  );

  if (!info) return null;

  const est = info.estimate;
  const pricing = info.state_snapshot.pricing_data || {};
  const canApprove = est.status === 'REVIEW_REQUIRED';
  const isApproved = est.status === 'APPROVED' || est.status === 'DISPATCHED';

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShieldAlert className="text-amber-400" size={24} />
            Approval Gateway
          </h1>
          <p className="text-gray-400 text-sm">Estimate {typeof id === 'string' ? id.slice(0, 8) : id}... — Senior Estimator sign-off required</p>
        </div>
        <StatusPill status={est.status} />
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">{error}</div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-900/30 border border-green-700 rounded-lg text-green-300 text-sm flex items-center gap-2">
          <CheckCircle size={16} /> {success}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
            <DollarSign size={12} /> Contract Value
          </div>
          <p className="text-xl font-bold">AED {est.total_aed.toLocaleString()}</p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
            <ClipboardList size={12} /> BOM Items
          </div>
          <p className="text-xl font-bold">{est.bom_items_count}</p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
            <ShieldAlert size={12} /> Compliance
          </div>
          <p className="text-xl font-bold">
            {est.compliance_passed === null ? '—' :
              est.compliance_passed
                ? <span className="text-green-400">PASS</span>
                : <span className="text-red-400">FAIL</span>}
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
            <Zap size={12} /> VE Savings
          </div>
          <p className="text-xl font-bold text-green-400">AED {est.ve_accepted_savings.toLocaleString()}</p>
        </div>
      </div>

      {/* Financial breakdown */}
      {Object.keys(pricing).length > 0 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
          <h2 className="font-bold mb-4 flex items-center gap-2">
            <BarChart3 size={18} className="text-blue-400" />
            Financial Breakdown
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            {[
              ['Aluminum', pricing.aluminum_cost_aed],
              ['Glass', pricing.glass_cost_aed],
              ['Hardware', pricing.hardware_cost_aed],
              ['Labor', pricing.labor_cost_aed],
              ['Attic Stock (2%)', pricing.attic_stock_cost_aed],
              ['Overhead', pricing.overhead_aed],
              ['Margin (18%)', pricing.margin_aed],
              ['Provisional Sums', pricing.provisional_sums_aed],
            ].filter(([, v]) => v !== undefined && v !== null).map(([label, value]) => (
              <div key={label as string} className="flex justify-between border-b border-gray-800 pb-2">
                <span className="text-gray-400">{label as string}</span>
                <span className="font-mono">AED {(value as number).toLocaleString()}</span>
              </div>
            ))}
            <div className="flex justify-between col-span-2 lg:col-span-3 pt-2 font-bold text-lg">
              <span>Total Contract Value</span>
              <span className="text-white">AED {est.total_aed.toLocaleString()}</span>
            </div>
          </div>

          {pricing.retention_note && (
            <div className="mt-4 p-3 bg-amber-900/20 border border-amber-700/30 rounded-lg text-amber-300 text-xs">
              ⚠ {pricing.retention_note}
            </div>
          )}
          {pricing.delivery_terms && (
            <div className="mt-2 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg text-blue-300 text-xs">
              📦 {pricing.delivery_terms}
            </div>
          )}
        </div>
      )}

      {/* Approval action */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
        <h2 className="font-bold mb-3 flex items-center gap-2">
          <CheckCircle size={18} className="text-green-400" />
          Final Sign-Off
        </h2>

        {isApproved ? (
          <div className="flex items-center gap-3 text-green-400">
            <CheckCircle size={24} />
            <div>
              <p className="font-semibold">Estimate Approved</p>
              {est.approved_by && <p className="text-sm text-gray-400">By: {est.approved_by}</p>}
              {est.approved_at && <p className="text-sm text-gray-400">At: {new Date(est.approved_at).toLocaleString()}</p>}
            </div>
          </div>
        ) : canApprove ? (
          <div>
            <p className="text-gray-400 text-sm mb-4">
              By approving this estimate, you confirm that all BOQ items, pricing, compliance checks,
              and VE decisions have been reviewed. Report generation will begin immediately after approval.
            </p>
            <button
              onClick={handleApprove}
              disabled={approving}
              className="flex items-center gap-2 px-6 py-3 bg-green-700 hover:bg-green-600 rounded-xl font-semibold transition-colors disabled:opacity-50"
            >
              {approving ? <Loader size={18} className="animate-spin" /> : <CheckCircle size={18} />}
              {approving ? 'Processing...' : 'Approve & Generate Reports'}
            </button>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">
            Estimate is in status <strong>{est.status}</strong> — approval not available in this state.
          </p>
        )}
      </div>

      {/* Nav links */}
      <div className="mt-6 flex gap-3 flex-wrap">
        {[
          { label: 'Compliance Report', path: `/estimate/${id}/compliance` },
          { label: 'VE Menu', path: `/estimate/${id}/ve-menu` },
          { label: 'RFI Log', path: `/estimate/${id}/rfi` },
          { label: 'Back to Estimate', path: `/estimate/${id}` },
        ].map(({ label, path }) => (
          <button
            key={path}
            onClick={() => router.push(path)}
            className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
