import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Archive, Briefcase, Clock, ChevronRight, AlertCircle } from 'lucide-react';
import { apiGet } from '../../lib/api';

interface EstimateSummary {
  estimate_id: string;
  project_id: string;
  status: string;
  progress_pct: number;
  current_step: string;
  created_at: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  APPROVED: 'bg-emerald-100 text-emerald-700',
  DISPATCHED: 'bg-purple-100 text-purple-700',
  REVIEW_REQUIRED: 'bg-amber-100 text-amber-700',
  Complete: 'bg-emerald-100 text-emerald-700',
  Error: 'bg-red-100 text-red-700',
  Processing: 'bg-blue-100 text-blue-700',
  Queued: 'bg-slate-100 text-slate-600',
};

export default function ArchivePage() {
  const [estimates, setEstimates] = useState<EstimateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<EstimateSummary[]>('/api/ingestion/estimates')
      .then(setEstimates)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-slate-50">
      <div className="mb-6 flex items-center gap-3">
        <Archive size={24} className="text-blue-600" />
        <div>
          <h2 className="text-xl font-black text-slate-800 uppercase tracking-tight">Project Archive</h2>
          <p className="text-xs text-slate-500 mt-0.5">All estimates for your organisation</p>
        </div>
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-white border border-slate-200 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      {!loading && !error && estimates.length === 0 && (
        <div className="bg-white border border-slate-200 p-16 text-center rounded-xl">
          <Archive size={40} className="mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500 text-sm">No estimates found. Upload your first project to get started.</p>
          <Link
            href="/estimate/new"
            className="mt-4 inline-block px-5 py-2.5 bg-blue-600 text-white rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-blue-700 transition-all"
          >
            New Estimate
          </Link>
        </div>
      )}

      {!loading && estimates.length > 0 && (
        <div className="space-y-2">
          {estimates.map((e) => (
            <Link
              key={e.estimate_id}
              href={`/estimate/${e.estimate_id}`}
              className="flex items-center gap-4 bg-white border border-slate-200 rounded-xl p-4 hover:border-blue-300 hover:shadow-sm transition-all group"
            >
              <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 flex-shrink-0">
                <Briefcase size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-800 font-mono">
                    {e.estimate_id.slice(0, 8).toUpperCase()}
                  </span>
                  <span className={`text-[9px] font-bold px-2 py-0.5 rounded uppercase ${STATUS_COLORS[e.status] || STATUS_COLORS['Queued']}`}>
                    {e.status}
                  </span>
                  {e.progress_pct > 0 && e.progress_pct < 100 && (
                    <span className="text-[9px] font-mono text-blue-600">{e.progress_pct}%</span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Clock size={10} />
                    {e.created_at ? new Date(e.created_at).toLocaleDateString() : '—'}
                  </span>
                  <span className="truncate">{e.current_step || 'Pending'}</span>
                </div>
              </div>
              <ChevronRight size={16} className="text-slate-300 group-hover:text-blue-600 transition-colors flex-shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
