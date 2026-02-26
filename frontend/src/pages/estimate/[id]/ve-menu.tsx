/**
 * C11 -- Dynamic Value Engineering Menu
 * Per-item accept/reject with live running savings total.
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { TrendingDown, CheckCircle, XCircle, Loader2, RefreshCw, ArrowLeft, AlertTriangle } from 'lucide-react';
import { apiGet, apiPut } from '../../../lib/api';

interface VEItem {
  ve_id: string;
  description: string;
  category: string;
  saving_aed: number;
  saving_pct: number;
  technical_impact: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  status: 'PENDING' | 'ACCEPTED' | 'REJECTED';
  accepted_by: string | null;
  rejected_reason: string | null;
}

interface VEMenu {
  total_ve_items: number;
  total_potential_savings_aed: number;
  accepted_savings_aed: number;
  contract_value_aed: number;
  items: VEItem[];
}

const riskColors: Record<string, string> = {
  LOW: 'text-green-600',
  MEDIUM: 'text-amber-600',
  HIGH: 'text-red-600',
};

const riskBadge: Record<string, string> = {
  LOW: 'bg-green-50 text-green-700 border-green-200',
  MEDIUM: 'bg-amber-50 text-amber-700 border-amber-200',
  HIGH: 'bg-red-50 text-red-700 border-red-200',
};

export default function VEMenuPage() {
  const router = useRouter();
  const { id } = router.query;
  const [menu, setMenu] = useState<VEMenu | null>(null);
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [rejectionModal, setRejectionModal] = useState<{ veId: string; reason: string } | null>(null);

  const fetchMenu = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const data = await apiGet<VEMenu>(`/api/commercial/${id}/ve-menu`);
      setMenu(data);
    } catch (e: any) {
      const msg = e.message || '';
      if (msg.includes('404') || msg.includes('not found') || msg.includes('Not Found')) {
        setNotFound(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMenu(); }, [id]);

  const decide = async (veId: string, decision: 'ACCEPTED' | 'REJECTED', rejectionReason?: string) => {
    if (!id) return;
    setDeciding(veId);
    setError(null);
    try {
      const result = await apiPut<{
        accepted_savings_aed: number;
        total_potential_savings_aed: number;
      }>(`/api/commercial/${id}/ve/${veId}`, {
        decision,
        decided_by: 'estimator',
        rejection_reason: rejectionReason || '',
      });

      setMenu((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          accepted_savings_aed: result.accepted_savings_aed,
          items: prev.items.map((item) =>
            item.ve_id === veId
              ? { ...item, status: decision, rejected_reason: rejectionReason || null }
              : item
          ),
        };
      });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeciding(null);
      setRejectionModal(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="animate-spin text-slate-400" size={28} />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-3">
          <TrendingDown size={36} className="mx-auto text-slate-300" />
          <p className="text-slate-600 font-medium">No VE data available</p>
          <p className="text-xs text-slate-400">Value engineering analysis has not been run for this estimate yet.</p>
          <Link href={`/estimate/${id}`} className="text-sm text-blue-600 hover:underline inline-block mt-2">
            Back to Estimate
          </Link>
        </div>
      </div>
    );
  }

  if (error && !menu) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-3">
          <AlertTriangle size={36} className="mx-auto text-red-400" />
          <p className="text-slate-600 font-medium">Failed to load VE menu</p>
          <p className="text-xs text-red-500 max-w-md">{error}</p>
          <Link href={`/estimate/${id}`} className="text-sm text-blue-600 hover:underline inline-block mt-2">
            Back to Estimate
          </Link>
        </div>
      </div>
    );
  }

  if (!menu) return null;

  const pendingCount = menu.items.filter((i) => i.status === 'PENDING').length;
  const savingsCapture = menu.total_potential_savings_aed > 0
    ? (menu.accepted_savings_aed / menu.total_potential_savings_aed * 100).toFixed(0)
    : '0';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/estimate/${id}`} className="p-1.5 hover:bg-slate-100 rounded-md transition-colors">
            <ArrowLeft size={18} className="text-slate-400" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <TrendingDown size={20} className="text-green-600" />
              Value Engineering Menu
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">Accept or reject each VE opportunity -- BOQ updates automatically</p>
          </div>
        </div>
        <button onClick={fetchMenu} className="p-2 rounded-md border border-slate-200 hover:bg-slate-50 transition-colors text-slate-500">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <p className="text-slate-500 text-xs mb-1">Potential Savings</p>
          <p className="text-lg font-semibold text-green-600 font-mono">AED {menu.total_potential_savings_aed.toLocaleString()}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <p className="text-slate-500 text-xs mb-1">Accepted Savings</p>
          <p className="text-lg font-semibold text-slate-800 font-mono">AED {menu.accepted_savings_aed.toLocaleString()}</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <p className="text-slate-500 text-xs mb-1">Capture Rate</p>
          <p className="text-lg font-semibold text-blue-600 font-mono">{savingsCapture}%</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <p className="text-slate-500 text-xs mb-1">Items Pending</p>
          <p className="text-lg font-semibold text-amber-600">{pendingCount} / {menu.total_ve_items}</p>
        </div>
      </div>

      {/* Savings progress bar */}
      <div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 rounded-full transition-all duration-700"
            style={{ width: `${savingsCapture}%` }}
          />
        </div>
        <p className="text-xs text-slate-400 mt-1">
          AED {menu.accepted_savings_aed.toLocaleString()} accepted of AED {menu.total_potential_savings_aed.toLocaleString()} potential
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm flex items-center gap-2">
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {/* VE Items */}
      <div className="space-y-3">
        {menu.items.map((item) => (
          <div
            key={item.ve_id}
            className={`bg-white border rounded-lg p-5 transition-all ${
              item.status === 'ACCEPTED' ? 'border-green-200 bg-green-50/30' :
              item.status === 'REJECTED' ? 'border-slate-200 opacity-60' :
              'border-slate-200'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded border border-slate-200 font-mono">
                    {item.ve_id}
                  </span>
                  <span className="text-xs text-slate-500">{item.category}</span>
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded border ${riskBadge[item.risk_level] || ''}`}>
                    {item.risk_level} risk
                  </span>
                </div>

                <p className="text-slate-700 text-sm mb-1">{item.description}</p>

                {item.technical_impact && item.technical_impact !== 'None' && (
                  <p className="text-slate-400 text-xs">Technical impact: {item.technical_impact}</p>
                )}

                {item.status === 'REJECTED' && item.rejected_reason && (
                  <p className="text-red-600 text-xs mt-1">Rejected: {item.rejected_reason}</p>
                )}
              </div>

              <div className="text-right shrink-0">
                <div className="text-green-600 font-semibold text-base font-mono mb-0.5">
                  AED {item.saving_aed.toLocaleString()}
                </div>
                <div className="text-slate-400 text-xs mb-3">{item.saving_pct.toFixed(1)}% saving</div>

                {item.status === 'PENDING' && (
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => decide(item.ve_id, 'ACCEPTED')}
                      disabled={deciding === item.ve_id}
                      className="flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-md text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      {deciding === item.ve_id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />}
                      Accept
                    </button>
                    <button
                      onClick={() => setRejectionModal({ veId: item.ve_id, reason: '' })}
                      disabled={deciding === item.ve_id}
                      className="flex items-center gap-1 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-md text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      <XCircle size={12} />
                      Reject
                    </button>
                  </div>
                )}

                {item.status === 'ACCEPTED' && (
                  <span className="flex items-center gap-1 text-green-600 text-sm justify-end">
                    <CheckCircle size={14} /> Accepted
                  </span>
                )}
                {item.status === 'REJECTED' && (
                  <span className="flex items-center gap-1 text-slate-400 text-sm justify-end">
                    <XCircle size={14} /> Rejected
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Rejection modal */}
      {rejectionModal && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
          <div className="bg-white border border-slate-200 rounded-lg p-6 w-full max-w-md shadow-xl">
            <h3 className="font-semibold text-slate-800 mb-3">Reject VE Item {rejectionModal.veId}</h3>
            <textarea
              className="w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-sm h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              placeholder="Reason for rejection (optional)..."
              value={rejectionModal.reason}
              onChange={(e) => setRejectionModal({ ...rejectionModal, reason: e.target.value })}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => decide(rejectionModal.veId, 'REJECTED', rejectionModal.reason)}
                className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium transition-colors"
              >
                Confirm Rejection
              </button>
              <button
                onClick={() => setRejectionModal(null)}
                className="px-4 py-2 border border-slate-200 hover:bg-slate-50 rounded-md text-sm text-slate-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
