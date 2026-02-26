/**
 * C11 — Dynamic Value Engineering Menu
 * Per-item accept/reject with live running savings total.
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { TrendingDown, CheckCircle, XCircle, Loader, DollarSign, RefreshCw } from 'lucide-react';
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
  LOW: 'text-green-400',
  MEDIUM: 'text-yellow-400',
  HIGH: 'text-red-400',
};

export default function VEMenuPage() {
  const router = useRouter();
  const { id } = router.query;
  const [menu, setMenu] = useState<VEMenu | null>(null);
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rejectionModal, setRejectionModal] = useState<{ veId: string; reason: string } | null>(null);

  const fetchMenu = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await apiGet<VEMenu>(`/api/commercial/${id}/ve-menu`);
      setMenu(data);
    } catch (e: any) {
      setError(e.message);
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

      // Optimistically update menu
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

  const pendingCount = menu?.items.filter((i) => i.status === 'PENDING').length || 0;
  const acceptedCount = menu?.items.filter((i) => i.status === 'ACCEPTED').length || 0;

  if (loading) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <Loader className="animate-spin text-blue-400" size={32} />
    </div>
  );

  if (error && !menu) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center text-red-400">
      <XCircle size={32} className="mr-2" /> {error}
    </div>
  );

  if (!menu) return null;

  const savingsCapture = menu.total_potential_savings_aed > 0
    ? (menu.accepted_savings_aed / menu.total_potential_savings_aed * 100).toFixed(0)
    : '0';

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <TrendingDown className="text-green-400" size={24} />
            Value Engineering Menu
          </h1>
          <p className="text-gray-400 text-sm">Accept or reject each VE opportunity — BOQ updates automatically</p>
        </div>
        <button onClick={fetchMenu} className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Savings Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Potential Savings</p>
          <p className="text-xl font-bold text-green-400">AED {menu.total_potential_savings_aed.toLocaleString()}</p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Accepted Savings</p>
          <p className="text-xl font-bold text-white">AED {menu.accepted_savings_aed.toLocaleString()}</p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Savings Captured</p>
          <p className="text-xl font-bold text-blue-400">{savingsCapture}%</p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Items Pending</p>
          <p className="text-xl font-bold text-amber-400">{pendingCount} / {menu.total_ve_items}</p>
        </div>
      </div>

      {/* Savings bar */}
      <div className="mb-8">
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-600 to-green-400 rounded-full transition-all duration-700"
            style={{ width: `${savingsCapture}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">
          AED {menu.accepted_savings_aed.toLocaleString()} accepted of AED {menu.total_potential_savings_aed.toLocaleString()} potential
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">{error}</div>
      )}

      {/* VE Items */}
      <div className="space-y-3">
        {menu.items.map((item) => (
          <div
            key={item.ve_id}
            className={`bg-gray-900 border rounded-xl p-5 transition-all ${
              item.status === 'ACCEPTED' ? 'border-green-700/50 bg-green-900/10' :
              item.status === 'REJECTED' ? 'border-gray-700 opacity-60' :
              'border-gray-700'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                {/* Meta */}
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs px-2 py-0.5 bg-blue-900/30 text-blue-300 rounded-full border border-blue-700/30">
                    {item.ve_id}
                  </span>
                  <span className="text-xs text-gray-500">{item.category}</span>
                  <span className={`text-xs font-medium ${riskColors[item.risk_level]}`}>
                    {item.risk_level} risk
                  </span>
                </div>

                {/* Description */}
                <p className="text-gray-200 text-sm mb-2">{item.description}</p>

                {/* Technical impact */}
                {item.technical_impact && item.technical_impact !== 'None' && (
                  <p className="text-gray-500 text-xs">Technical impact: {item.technical_impact}</p>
                )}

                {/* Rejection reason */}
                {item.status === 'REJECTED' && item.rejected_reason && (
                  <p className="text-red-400 text-xs mt-1">Rejected: {item.rejected_reason}</p>
                )}
              </div>

              {/* Saving + Actions */}
              <div className="text-right flex-shrink-0">
                <div className="text-green-400 font-bold text-lg mb-1">
                  AED {item.saving_aed.toLocaleString()}
                </div>
                <div className="text-gray-500 text-xs mb-3">{item.saving_pct.toFixed(1)}% saving</div>

                {item.status === 'PENDING' && (
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => decide(item.ve_id, 'ACCEPTED')}
                      disabled={deciding === item.ve_id}
                      className="flex items-center gap-1 px-3 py-1.5 bg-green-700 hover:bg-green-600 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      {deciding === item.ve_id ? <Loader size={12} className="animate-spin" /> : <CheckCircle size={12} />}
                      Accept
                    </button>
                    <button
                      onClick={() => setRejectionModal({ veId: item.ve_id, reason: '' })}
                      disabled={deciding === item.ve_id}
                      className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      <XCircle size={12} />
                      Reject
                    </button>
                  </div>
                )}

                {item.status === 'ACCEPTED' && (
                  <span className="flex items-center gap-1 text-green-400 text-sm justify-end">
                    <CheckCircle size={14} /> Accepted
                  </span>
                )}
                {item.status === 'REJECTED' && (
                  <span className="flex items-center gap-1 text-gray-500 text-sm justify-end">
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
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
            <h3 className="font-bold mb-3">Reject VE Item {rejectionModal.veId}</h3>
            <textarea
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm h-24 resize-none focus:outline-none focus:border-blue-500"
              placeholder="Reason for rejection (optional)..."
              value={rejectionModal.reason}
              onChange={(e) => setRejectionModal({ ...rejectionModal, reason: e.target.value })}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => decide(rejectionModal.veId, 'REJECTED', rejectionModal.reason)}
                className="flex-1 py-2 bg-red-700 hover:bg-red-600 rounded-lg text-sm font-medium transition-colors"
              >
                Confirm Rejection
              </button>
              <button
                onClick={() => setRejectionModal(null)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
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
