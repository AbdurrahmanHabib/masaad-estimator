import React from 'react';
import Link from 'next/link';
import {
  Briefcase,
  TrendingUp,
  Clock,
  ChevronRight,
  AlertCircle,
  MapPin,
  Building2,
  Plus,
  FileText,
  Loader2,
  Trash2,
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { apiGet, apiDelete } from '../lib/api';

// Types

interface DashboardSummary {
  total_projects?: number;
  total_estimates?: number;
  active_processing?: number;
  factory_margin_pct?: number;
  technical_rfis?: number;
  optimization_gaps?: number;
}

interface RecentEstimate {
  estimate_id: string;
  project_id?: string;
  project_name?: string;
  client_name?: string;
  location?: string;
  status: string;
  progress_pct?: number;
  current_step?: string;
  total_sell_price_aed?: number;
  created_at?: string;
}

const STATUS_STYLES: Record<string, string> = {
  ESTIMATING: 'bg-blue-50 text-[#002147] border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  DISPATCHED: 'bg-purple-50 text-purple-700 border-purple-200',
  Completed: 'bg-slate-50 text-[#64748b] border-slate-200',
  Queued: 'bg-blue-50 text-[#002147] border-blue-200',
  Failed: 'bg-red-50 text-red-600 border-red-200',
};

export default function Dashboard() {
  const { user } = useAuthStore();
  const [summary, setSummary] = React.useState<DashboardSummary | null>(null);
  const [recentEstimates, setRecentEstimates] = React.useState<RecentEstimate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [lastSyncTime, setLastSyncTime] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLastSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  }, []);

  React.useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await apiGet<DashboardSummary>('/api/dashboard/summary');
        setSummary(data);
      } catch {
        // Keep null
      }

      try {
        const data = await apiGet<RecentEstimate[]>('/api/v1/estimates/recent');
        if (Array.isArray(data) && data.length > 0) {
          setRecentEstimates(data);
        }
      } catch {
        // Non-fatal
      }

      setLoading(false);
    };

    fetchData();
  }, []);

  const handleDelete = async (estimateId: string, projectName?: string) => {
    const name = projectName || estimateId.slice(0, 12);
    if (!window.confirm(`Delete "${name}"? This action cannot be undone.`)) return;
    try {
      await apiDelete(`/api/v1/estimates/${estimateId}`);
      setRecentEstimates(prev => prev.filter(e => e.estimate_id !== estimateId));
    } catch (err: any) {
      alert(err.message || 'Delete failed');
    }
  };

  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'Admin';
  const activeProjects = summary?.total_projects ?? summary?.active_processing ?? recentEstimates.length;
  const totalEstimates = summary?.total_estimates ?? recentEstimates.length;
  const reviewRequired = recentEstimates.filter(e => e.status === 'REVIEW_REQUIRED').length;

  return (
    <div className="space-y-6">
      {/* WELCOME BANNER */}
      <div className="bg-gradient-to-r from-[#002147] to-[#1e3a5f] rounded-md p-6 flex flex-col sm:flex-row justify-between sm:items-end gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">
            Welcome back, {firstName}
          </h1>
          <p className="text-white/60 text-sm mt-1">
            Here is an overview of your estimation projects.
          </p>
        </div>
        <Link
          href="/estimate/new"
          className="px-5 py-2.5 bg-[#002147] hover:bg-[#1e3a5f] border border-white/20 text-white rounded-md text-sm font-medium transition-all flex items-center gap-2 shrink-0"
        >
          <Plus size={16} /> New Estimation
        </Link>
      </div>

      {/* STAT CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Projects', value: activeProjects, icon: Briefcase, borderColor: 'border-l-[#3b82f6]' },
          { label: 'Total Estimates', value: totalEstimates, icon: FileText, borderColor: 'border-l-[#059669]' },
          { label: 'Pending Review', value: reviewRequired, icon: AlertCircle, borderColor: 'border-l-[#d97706]' },
          { label: 'Factory Margin', value: summary?.factory_margin_pct !== undefined ? `${summary.factory_margin_pct}%` : '18%', icon: TrendingUp, borderColor: 'border-l-[#002147]' },
        ].map((card) => (
          <div key={card.label} className={`bg-white border border-[#e2e8f0] border-l-4 ${card.borderColor} rounded-md p-6 shadow-sm`}>
            <div className="flex items-center gap-2 mb-3">
              <card.icon size={16} className="text-[#64748b]" />
              <span className="text-xs font-medium text-[#64748b]">{card.label}</span>
            </div>
            {loading ? (
              <div className="h-7 bg-slate-100 rounded animate-pulse w-16" />
            ) : (
              <p className="text-2xl font-bold text-[#1e293b] font-mono">{card.value}</p>
            )}
          </div>
        ))}
      </div>

      {/* RECENT ESTIMATES TABLE */}
      <div className="bg-white border border-[#e2e8f0] rounded-md overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-[#e2e8f0] flex justify-between items-center">
          <h3 className="text-sm font-semibold text-[#1e293b]">Recent Estimates</h3>
          <Link
            href="/estimate/new"
            className="text-xs text-[#002147] hover:text-[#1e3a5f] font-medium flex items-center gap-1 transition-colors"
          >
            New Estimation <ChevronRight size={12} />
          </Link>
        </div>

        {loading && recentEstimates.length === 0 && (
          <div className="px-6 py-12 flex justify-center">
            <Loader2 size={24} className="animate-spin text-slate-300" />
          </div>
        )}

        {!loading && recentEstimates.length === 0 && (
          <div className="px-6 py-12 text-center text-[#64748b]">
            <Building2 size={36} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm font-medium">No estimates yet</p>
            <p className="text-xs mt-1">Create your first estimation to get started.</p>
          </div>
        )}

        {recentEstimates.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#002147]">
                  <th className="text-left py-3 px-6 font-semibold text-white text-xs uppercase tracking-wider">Project</th>
                  <th className="text-left py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Client</th>
                  <th className="text-left py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Location</th>
                  <th className="text-left py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Status</th>
                  <th className="text-right py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Progress</th>
                  <th className="text-right py-3 px-6 font-semibold text-white text-xs uppercase tracking-wider"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e2e8f0]">
                {recentEstimates.map((est, idx) => {
                  const statusStyle = STATUS_STYLES[est.status] ?? 'bg-slate-50 text-[#64748b] border-slate-200';
                  return (
                    <tr key={est.estimate_id} className={idx % 2 === 1 ? 'bg-slate-50/50' : 'bg-white'}>
                      <td className="py-3 px-6">
                        <p className="font-medium text-[#1e293b]">
                          {est.project_name || est.estimate_id.slice(0, 12)}
                        </p>
                      </td>
                      <td className="py-3 px-4 text-[#64748b]">
                        {est.client_name || '--'}
                      </td>
                      <td className="py-3 px-4 text-[#64748b]">
                        {est.location ? (
                          <span className="flex items-center gap-1"><MapPin size={12} /> {est.location}</span>
                        ) : '--'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-0.5 text-[11px] font-semibold rounded-md border ${statusStyle}`}>
                          {est.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-[#1e293b]">
                        {est.progress_pct !== undefined ? `${est.progress_pct}%` : '--'}
                      </td>
                      <td className="py-3 px-6 text-right">
                        <div className="flex items-center justify-end gap-3">
                          <Link
                            href={`/estimate/${est.estimate_id}`}
                            className="text-xs text-[#002147] hover:text-[#1e3a5f] font-medium transition-colors"
                          >
                            Open
                          </Link>
                          <button
                            onClick={() => handleDelete(est.estimate_id, est.project_name)}
                            className="p-1 text-[#94a3b8] hover:text-red-500 transition-colors rounded hover:bg-red-50"
                            title="Delete estimate"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* SYNC FOOTER */}
      <div className="flex justify-center pb-4">
        <div className="flex items-center gap-2 text-xs text-[#64748b]">
          <Clock size={12} /> Last sync: {lastSyncTime || '...'}
        </div>
      </div>
    </div>
  );
}
