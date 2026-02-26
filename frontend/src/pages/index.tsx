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
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { apiGet } from '../lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

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
  ESTIMATING: 'bg-blue-50 text-blue-700 border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-green-50 text-green-700 border-green-200',
  DISPATCHED: 'bg-purple-50 text-purple-700 border-purple-200',
  Completed: 'bg-slate-50 text-slate-500 border-slate-200',
  Queued: 'bg-blue-50 text-blue-600 border-blue-200',
  Failed: 'bg-red-50 text-red-600 border-red-200',
};

// ─── Dashboard ────────────────────────────────────────────────────────────────

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
        // Keep null -- UI handles gracefully
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

  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'Admin';
  const activeProjects = summary?.total_projects ?? summary?.active_processing ?? recentEstimates.length;
  const totalEstimates = summary?.total_estimates ?? recentEstimates.length;
  const reviewRequired = recentEstimates.filter(e => e.status === 'REVIEW_REQUIRED').length;
  const rfis = summary?.technical_rfis ?? 0;

  return (
    <div className="space-y-8">
      {/* HEADER */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            Welcome back, {firstName}
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Here is an overview of your estimation projects.
          </p>
        </div>
        <Link
          href="/estimate/new"
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors flex items-center gap-2 shrink-0"
        >
          <Plus size={16} /> New Estimation
        </Link>
      </div>

      {/* STAT CARDS */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
            <Briefcase size={14} /> Active Projects
          </div>
          {loading ? (
            <div className="h-7 bg-slate-100 rounded animate-pulse w-16" />
          ) : (
            <p className="text-2xl font-bold text-slate-800 font-mono">{activeProjects}</p>
          )}
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
            <FileText size={14} /> Total Estimates
          </div>
          {loading ? (
            <div className="h-7 bg-slate-100 rounded animate-pulse w-16" />
          ) : (
            <p className="text-2xl font-bold text-slate-800 font-mono">{totalEstimates}</p>
          )}
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="flex items-center gap-2 text-amber-600 text-xs mb-2">
            <AlertCircle size={14} /> Pending Review
          </div>
          {loading ? (
            <div className="h-7 bg-slate-100 rounded animate-pulse w-16" />
          ) : (
            <p className="text-2xl font-bold text-slate-800 font-mono">{reviewRequired}</p>
          )}
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <div className="flex items-center gap-2 text-slate-500 text-xs mb-2">
            <TrendingUp size={14} /> Factory Margin
          </div>
          {loading ? (
            <div className="h-7 bg-slate-100 rounded animate-pulse w-16" />
          ) : (
            <p className="text-2xl font-bold text-slate-800 font-mono">
              {summary?.factory_margin_pct !== undefined ? `${summary.factory_margin_pct}%` : '18%'}
            </p>
          )}
        </div>
      </div>

      {/* RECENT ESTIMATES TABLE */}
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center">
          <h3 className="text-sm font-semibold text-slate-800">Recent Estimates</h3>
          <Link
            href="/estimate/new"
            className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1 transition-colors"
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
          <div className="px-6 py-12 text-center text-slate-400">
            <Building2 size={36} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm font-medium">No estimates yet</p>
            <p className="text-xs mt-1">Create your first estimation to get started.</p>
          </div>
        )}

        {recentEstimates.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left py-3 px-6 font-semibold text-slate-600 text-xs">Project</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-600 text-xs">Client</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-600 text-xs">Location</th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-600 text-xs">Status</th>
                  <th className="text-right py-3 px-4 font-semibold text-slate-600 text-xs">Progress</th>
                  <th className="text-right py-3 px-6 font-semibold text-slate-600 text-xs"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recentEstimates.map((est) => {
                  const statusStyle = STATUS_STYLES[est.status] ?? 'bg-slate-50 text-slate-500 border-slate-200';
                  return (
                    <tr key={est.estimate_id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="py-3 px-6">
                        <p className="font-medium text-slate-800">
                          {est.project_name || est.estimate_id.slice(0, 12)}
                        </p>
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {est.client_name || '--'}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {est.location ? (
                          <span className="flex items-center gap-1"><MapPin size={12} /> {est.location}</span>
                        ) : '--'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-0.5 text-[11px] font-semibold rounded border ${statusStyle}`}>
                          {est.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-slate-600">
                        {est.progress_pct !== undefined ? `${est.progress_pct}%` : '--'}
                      </td>
                      <td className="py-3 px-6 text-right">
                        <Link
                          href={`/estimate/${est.estimate_id}`}
                          className="text-xs text-blue-600 hover:text-blue-700 font-medium transition-colors"
                        >
                          Open
                        </Link>
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
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Clock size={12} /> Last sync: {lastSyncTime || '...'}
        </div>
      </div>
    </div>
  );
}
