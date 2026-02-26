/**
 * HITL Triage Queue -- Human-in-the-Loop review dashboard.
 * Lists all pending triage items where AI confidence < 90%.
 * Admin/Senior Estimator resolves items to unblock the pipeline.
 */
import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Loader2, RefreshCw, Eye } from 'lucide-react';
import { apiGet, apiPost } from '../../lib/api';

interface TriageItem {
  id: string;
  estimate_id: string;
  node_name: string;
  confidence_score: number;
  context_json: string;
  status: 'pending' | 'resolved' | 'skipped';
  created_at: string;
}

interface ResolutionForm {
  itemId: string;
  action: 'resolve' | 'skip';
  corrected_value: string;
  notes: string;
}

export default function TriagePage() {
  const [items, setItems] = useState<TriageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);
  const [form, setForm] = useState<ResolutionForm | null>(null);

  const fetchItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet<{ items: TriageItem[]; total: number }>('/api/v1/triage/pending');
      setItems(data.items || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
    const interval = setInterval(fetchItems, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleResolve = async () => {
    if (!form) return;
    setResolving(form.itemId);
    try {
      await apiPost(`/api/v1/triage/resolve/${form.itemId}`, {
        action: form.action,
        corrected_value: form.corrected_value,
        notes: form.notes,
      });
      setForm(null);
      await fetchItems();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setResolving(null);
    }
  };

  const parseContext = (ctx: string) => {
    try { return JSON.parse(ctx); } catch { return {}; }
  };

  const confidenceColor = (score: number) => {
    if (score >= 0.90) return 'text-[#059669]';
    if (score >= 0.75) return 'text-[#d97706]';
    return 'text-[#dc2626]';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-[#e2e8f0]">
        <div>
          <h1 className="text-xl font-bold text-[#002147] flex items-center gap-2">
            <AlertTriangle className="text-[#d97706]" size={20} />
            HITL Triage Queue
          </h1>
          <p className="text-[#64748b] text-sm mt-1">
            Items where AI confidence &lt; 90% -- requires human review before pipeline continues
          </p>
        </div>
        <button
          onClick={fetchItems}
          className="flex items-center gap-2 px-4 py-2 bg-[#002147] hover:bg-[#1e3a5f] text-white rounded-md text-sm transition-colors"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-[#dc2626] text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="animate-spin text-[#002147]" size={28} />
        </div>
      )}

      {/* Empty state */}
      {!loading && items.length === 0 && (
        <div className="flex flex-col items-center justify-center h-48 text-[#64748b]">
          <CheckCircle size={40} className="mb-3 text-[#059669]" />
          <p className="text-lg font-medium text-[#1e293b]">No pending triage items</p>
          <p className="text-sm">All estimates are processing with high confidence</p>
        </div>
      )}

      {/* Triage items */}
      {!loading && items.length > 0 && (
        <div className="space-y-4">
          {items.map((item) => {
            const ctx = parseContext(item.context_json);
            return (
              <div
                key={item.id}
                className="bg-white border border-[#e2e8f0] rounded-md p-6 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    {/* Badge row */}
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-2 py-0.5 bg-amber-50 text-[#d97706] text-xs rounded-md border border-amber-200 font-medium">
                        {item.node_name}
                      </span>
                      <span className={`font-mono text-sm font-bold ${confidenceColor(item.confidence_score)}`}>
                        {(item.confidence_score * 100).toFixed(0)}% confidence
                      </span>
                      <span className="text-[#64748b] text-xs">
                        Estimate: {item.estimate_id.slice(0, 8)}...
                      </span>
                    </div>

                    {/* Context */}
                    <p className="text-[#1e293b] text-sm mb-3">
                      Node failed confidence threshold in <strong>{item.node_name}</strong>.
                      {ctx.error && (
                        <span className="text-[#dc2626] ml-2">Error: {ctx.error}</span>
                      )}
                    </p>

                    {/* Raw context */}
                    <details className="text-xs text-[#64748b]">
                      <summary className="cursor-pointer flex items-center gap-1 hover:text-[#1e293b]">
                        <Eye size={12} /> View raw context
                      </summary>
                      <pre className="mt-2 bg-slate-50 p-3 rounded-md overflow-auto max-h-48 text-xs border border-[#e2e8f0]">
                        {JSON.stringify(ctx, null, 2)}
                      </pre>
                    </details>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => setForm({ itemId: item.id, action: 'resolve', corrected_value: '', notes: '' })}
                      className="flex items-center gap-1 px-3 py-1.5 bg-[#059669] hover:bg-[#047857] text-white rounded-md text-sm transition-colors"
                    >
                      <CheckCircle size={14} />
                      Resolve
                    </button>
                    <button
                      onClick={async () => {
                        setResolving(item.id);
                        try {
                          await apiPost(`/api/v1/triage/resolve/${item.id}`, { action: 'skip', notes: 'Skipped by reviewer' });
                          await fetchItems();
                        } catch (e: any) { setError(e.message); }
                        setResolving(null);
                      }}
                      disabled={resolving === item.id}
                      className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-[#64748b] rounded-md text-sm transition-colors disabled:opacity-50 border border-[#e2e8f0]"
                    >
                      {resolving === item.id ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
                      Skip
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Resolution modal */}
      {form && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white border border-[#e2e8f0] rounded-md p-6 w-full max-w-lg shadow-2xl">
            <h3 className="text-lg font-bold text-[#002147] mb-4">Resolve Triage Item</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#64748b] mb-1">Corrected Value (optional)</label>
                <input
                  className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#002147]/20 focus:border-[#002147] transition-all text-[#1e293b]"
                  placeholder="e.g. corrected die number, weight, etc."
                  value={form.corrected_value}
                  onChange={(e) => setForm({ ...form, corrected_value: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-[#64748b] mb-1">Notes</label>
                <textarea
                  className="w-full bg-slate-50 border border-[#e2e8f0] rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#002147]/20 focus:border-[#002147] h-24 resize-none transition-all text-[#1e293b]"
                  placeholder="Explain your resolution..."
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={handleResolve}
                disabled={resolving !== null}
                className="flex-1 py-2 bg-[#059669] hover:bg-[#047857] text-white rounded-md text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {resolving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                Confirm Resolution
              </button>
              <button
                onClick={() => setForm(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-[#e2e8f0] text-[#64748b] rounded-md text-sm transition-colors"
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
