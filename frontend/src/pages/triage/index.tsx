/**
 * HITL Triage Queue — Human-in-the-Loop review dashboard.
 * Lists all pending triage items where AI confidence < 90%.
 * Admin/Senior Estimator resolves items to unblock the pipeline.
 */
import React, { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Loader, RefreshCw, Eye } from 'lucide-react';
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
    // Poll every 15s for new items
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
    if (score >= 0.90) return 'text-green-400';
    if (score >= 0.75) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <AlertTriangle className="text-amber-400" size={24} />
            HITL Triage Queue
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Items where AI confidence &lt; 90% — requires human review before pipeline continues
          </p>
        </div>
        <button
          onClick={fetchItems}
          className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-48">
          <Loader className="animate-spin text-amber-400" size={32} />
        </div>
      )}

      {/* Empty state */}
      {!loading && items.length === 0 && (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500">
          <CheckCircle size={48} className="mb-3 text-green-500" />
          <p className="text-lg">No pending triage items</p>
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
                className="bg-gray-900 border border-gray-700 rounded-xl p-5"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    {/* Badge row */}
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 text-xs rounded-full border border-amber-500/30">
                        {item.node_name}
                      </span>
                      <span className={`font-mono text-sm font-bold ${confidenceColor(item.confidence_score)}`}>
                        {(item.confidence_score * 100).toFixed(0)}% confidence
                      </span>
                      <span className="text-gray-500 text-xs">
                        Estimate: {item.estimate_id.slice(0, 8)}...
                      </span>
                    </div>

                    {/* Context */}
                    <p className="text-gray-300 text-sm mb-3">
                      Node failed confidence threshold in <strong>{item.node_name}</strong>.
                      {ctx.error && (
                        <span className="text-red-400 ml-2">Error: {ctx.error}</span>
                      )}
                    </p>

                    {/* Raw context */}
                    <details className="text-xs text-gray-500">
                      <summary className="cursor-pointer flex items-center gap-1 hover:text-gray-400">
                        <Eye size={12} /> View raw context
                      </summary>
                      <pre className="mt-2 bg-gray-950 p-3 rounded overflow-auto max-h-48 text-xs">
                        {JSON.stringify(ctx, null, 2)}
                      </pre>
                    </details>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 ml-4">
                    <button
                      onClick={() => setForm({ itemId: item.id, action: 'resolve', corrected_value: '', notes: '' })}
                      className="flex items-center gap-1 px-3 py-1.5 bg-green-700 hover:bg-green-600 rounded-lg text-sm transition-colors"
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
                      className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors disabled:opacity-50"
                    >
                      {resolving === item.id ? <Loader size={14} className="animate-spin" /> : <XCircle size={14} />}
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
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg">
            <h3 className="text-lg font-bold mb-4">Resolve Triage Item</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Corrected Value (optional)</label>
                <input
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  placeholder="e.g. corrected die number, weight, etc."
                  value={form.corrected_value}
                  onChange={(e) => setForm({ ...form, corrected_value: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Notes</label>
                <textarea
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 h-24 resize-none"
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
                className="flex-1 py-2 bg-green-700 hover:bg-green-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {resolving ? <Loader size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                Confirm Resolution
              </button>
              <button
                onClick={() => setForm(null)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
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
