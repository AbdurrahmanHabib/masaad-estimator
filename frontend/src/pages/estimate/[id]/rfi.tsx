/**
 * C10 — Tender Clarification / RFI Log
 * Persistent log of all RFIs with overdue alerting.
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { MessageSquare, Clock, CheckCircle, AlertTriangle, Plus, Loader, RefreshCw } from 'lucide-react';
import { apiGet, apiPost, apiPut } from '../../../lib/api';

interface RFIItem {
  rfi_id: string;
  estimate_id: string;
  reference: string;
  text: string;
  source: string;
  status: 'OPEN' | 'RESPONDED';
  submitted_at: string;
  responded_at: string | null;
  response_text: string | null;
  days_open: number;
  overdue: boolean;
}

interface RFILog {
  estimate_id: string;
  rfi_log: RFIItem[];
  audit: {
    total_rfis: number;
    open_rfis: number;
    overdue_rfis: number;
    alert: string;
  };
}

interface AddRFIForm {
  rfi_text: string;
  reference: string;
}

interface RespondForm {
  rfi_id: string;
  response_text: string;
}

export default function RFILogPage() {
  const router = useRouter();
  const { id } = router.query;
  const [data, setData] = useState<RFILog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addForm, setAddForm] = useState<AddRFIForm | null>(null);
  const [respondForm, setRespondForm] = useState<RespondForm | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchLog = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const result = await apiGet<RFILog>(`/api/commercial/${id}/rfi-log`);
      setData(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLog(); }, [id]);

  const handleAdd = async () => {
    if (!addForm || !id) return;
    setSubmitting(true);
    try {
      await apiPost(`/api/commercial/${id}/rfi-log`, addForm);
      setAddForm(null);
      await fetchLog();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRespond = async () => {
    if (!respondForm || !id) return;
    setSubmitting(true);
    try {
      await apiPut(`/api/commercial/${id}/rfi/${respondForm.rfi_id}/respond`, {
        response_text: respondForm.response_text,
      });
      setRespondForm(null);
      await fetchLog();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <Loader className="animate-spin text-blue-400" size={32} />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <MessageSquare className="text-blue-400" size={24} />
            Tender Clarification Log
          </h1>
          <p className="text-gray-400 text-sm">RFIs raised during estimation — track responses</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchLog} className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700">
            <RefreshCw size={16} />
          </button>
          <button
            onClick={() => setAddForm({ rfi_text: '', reference: '' })}
            className="flex items-center gap-2 px-4 py-2 bg-blue-700 hover:bg-blue-600 rounded-lg text-sm font-medium transition-colors"
          >
            <Plus size={14} /> Add RFI
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">{error}</div>
      )}

      {/* Audit summary */}
      {data?.audit && (
        <div className={`mb-6 p-4 rounded-xl border ${data.audit.overdue_rfis > 0 ? 'bg-red-900/20 border-red-700/40' : 'bg-gray-900 border-gray-700'}`}>
          <div className="flex items-center justify-between">
            <div className="flex gap-6">
              <span className="text-sm"><span className="text-2xl font-bold text-white">{data.audit.total_rfis}</span> <span className="text-gray-400">total</span></span>
              <span className="text-sm"><span className="text-2xl font-bold text-amber-400">{data.audit.open_rfis}</span> <span className="text-gray-400">open</span></span>
              <span className="text-sm"><span className="text-2xl font-bold text-red-400">{data.audit.overdue_rfis}</span> <span className="text-gray-400">overdue</span></span>
            </div>
            {data.audit.overdue_rfis > 0 && (
              <div className="flex items-center gap-2 text-red-300 text-sm">
                <AlertTriangle size={16} />
                {data.audit.alert}
              </div>
            )}
          </div>
        </div>
      )}

      {/* RFI list */}
      {!data || data.rfi_log.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500">
          <MessageSquare size={48} className="mb-3" />
          <p>No RFIs raised yet</p>
        </div>
      ) : (
        <div className="space-y-4">
          {data.rfi_log.map((rfi) => (
            <div
              key={rfi.rfi_id}
              className={`bg-gray-900 border rounded-xl p-5 ${
                rfi.overdue ? 'border-red-700/50' :
                rfi.status === 'RESPONDED' ? 'border-green-700/30 opacity-80' :
                'border-gray-700'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-xs text-blue-300">{rfi.rfi_id}</span>
                    {rfi.reference && <span className="text-xs text-gray-500">ref: {rfi.reference}</span>}
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      rfi.source === 'compliance' ? 'bg-orange-900/30 text-orange-300' :
                      rfi.source === 'auto' ? 'bg-purple-900/30 text-purple-300' :
                      'bg-gray-700 text-gray-400'
                    }`}>{rfi.source}</span>
                    {rfi.overdue && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-900/30 text-red-300 flex items-center gap-1">
                        <AlertTriangle size={10} /> OVERDUE
                      </span>
                    )}
                  </div>

                  <p className="text-gray-200 text-sm whitespace-pre-wrap mb-2">{rfi.text}</p>

                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock size={10} />
                      Raised: {new Date(rfi.submitted_at).toLocaleDateString()}
                    </span>
                    {rfi.days_open > 0 && (
                      <span className={rfi.overdue ? 'text-red-400' : ''}>
                        {rfi.days_open} day(s) open
                      </span>
                    )}
                  </div>

                  {rfi.status === 'RESPONDED' && rfi.response_text && (
                    <div className="mt-3 p-3 bg-green-900/20 border border-green-700/30 rounded-lg">
                      <p className="text-xs text-green-400 mb-1">Response ({new Date(rfi.responded_at!).toLocaleDateString()})</p>
                      <p className="text-sm text-gray-300">{rfi.response_text}</p>
                    </div>
                  )}
                </div>

                <div className="flex-shrink-0">
                  {rfi.status === 'OPEN' ? (
                    <button
                      onClick={() => setRespondForm({ rfi_id: rfi.rfi_id, response_text: '' })}
                      className="flex items-center gap-1 px-3 py-1.5 bg-green-700 hover:bg-green-600 rounded-lg text-xs transition-colors"
                    >
                      <CheckCircle size={12} /> Respond
                    </button>
                  ) : (
                    <span className="flex items-center gap-1 text-green-400 text-xs">
                      <CheckCircle size={12} /> Responded
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add RFI modal */}
      {addForm !== null && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg">
            <h3 className="font-bold mb-4">Add RFI</h3>
            <div className="space-y-3">
              <input
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm"
                placeholder="Reference (e.g. drawing number, clause)"
                value={addForm.reference}
                onChange={(e) => setAddForm({ ...addForm, reference: e.target.value })}
              />
              <textarea
                className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm h-32 resize-none"
                placeholder="RFI text..."
                value={addForm.rfi_text}
                onChange={(e) => setAddForm({ ...addForm, rfi_text: e.target.value })}
              />
            </div>
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleAdd}
                disabled={submitting || !addForm.rfi_text}
                className="flex-1 py-2 bg-blue-700 hover:bg-blue-600 rounded-lg text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {submitting ? <Loader size={14} className="animate-spin" /> : <Plus size={14} />}
                Submit RFI
              </button>
              <button onClick={() => setAddForm(null)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Respond modal */}
      {respondForm !== null && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg">
            <h3 className="font-bold mb-4">Respond to {respondForm.rfi_id}</h3>
            <textarea
              className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-sm h-32 resize-none"
              placeholder="Client response / resolution..."
              value={respondForm.response_text}
              onChange={(e) => setRespondForm({ ...respondForm, response_text: e.target.value })}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleRespond}
                disabled={submitting || !respondForm.response_text}
                className="flex-1 py-2 bg-green-700 hover:bg-green-600 rounded-lg text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {submitting ? <Loader size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                Submit Response
              </button>
              <button onClick={() => setRespondForm(null)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
