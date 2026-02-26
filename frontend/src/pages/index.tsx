import React from 'react';
import Link from 'next/link';
import {
  Briefcase,
  TrendingUp,
  Clock,
  ChevronRight,
  Target,
  Zap,
  ShieldCheck,
  AlertCircle,
  MapPin,
  Globe,
  Building2,
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
  projects?: Array<{
    project_ref: string;
    client_name: string;
    region: string;
    status: string;
  }>;
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
  bom_summary?: Record<string, unknown>;
}

const STATUS_COLORS: Record<string, string> = {
  ESTIMATING: 'bg-blue-100 text-blue-700 border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-100 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  DISPATCHED: 'bg-purple-100 text-purple-700 border-purple-200',
  Completed: 'bg-slate-100 text-slate-500 border-slate-200',
  Queued: 'bg-blue-100 text-blue-600 border-blue-200',
  Failed: 'bg-red-100 text-red-600 border-red-200',
};

// ─── Skeleton component ───────────────────────────────────────────────────────

function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-slate-200 rounded-lg ${className}`} />
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user } = useAuthStore();
  const [summary, setSummary] = React.useState<DashboardSummary | null>(null);
  const [recentEstimates, setRecentEstimates] = React.useState<RecentEstimate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [lastSyncTime, setLastSyncTime] = React.useState<string | null>(null);

  // Client-only sync time to avoid hydration mismatch
  React.useEffect(() => {
    setLastSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  }, []);

  React.useEffect(() => {
    const fetchSummary = async () => {
      setLoading(true);
      try {
        const data = await apiGet<DashboardSummary>('/api/dashboard/summary');
        setSummary(data);
      } catch {
        // Keep null — UI handles gracefully with static fallbacks
      } finally {
        setLoading(false);
      }
    };

    const fetchRecentEstimates = async () => {
      try {
        const data = await apiGet<RecentEstimate[]>('/api/v1/estimates/recent');
        if (Array.isArray(data) && data.length > 0) {
          setRecentEstimates(data);
        }
      } catch {
        // Non-fatal — show empty state
      }
    };

    fetchSummary();
    fetchRecentEstimates();
  }, []);

  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'Admin';

  const activeProjects = summary?.total_projects ?? summary?.active_processing;
  const totalEstimates = summary?.total_estimates ?? recentEstimates.length;
  const marginPct = summary?.factory_margin_pct;
  const rfis = summary?.technical_rfis;
  const gaps = summary?.optimization_gaps;

  // Featured project: first estimate with REVIEW_REQUIRED status, or the first estimate
  const featuredEstimate = recentEstimates.find(e => e.status === 'REVIEW_REQUIRED') ?? recentEstimates[0];
  const isInternational = featuredEstimate?.location && !featuredEstimate.location.toLowerCase().includes('uae');

  return (
    <div className="space-y-10">
      {/* WELCOME SECTION */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-800 uppercase tracking-tighter italic">
            Welcome back, {firstName}
          </h1>
          <p className="text-slate-500 font-medium text-sm mt-1">
            Here is what is happening with your estimations today.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/estimate/new"
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-600/20 flex items-center gap-2"
          >
            <Zap size={14} /> New Estimation
          </Link>
          <button className="px-6 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm">
            Generate Reports
          </button>
        </div>
      </div>

      {/* QUICK ACTIONS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 group hover:border-blue-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 mb-4 group-hover:scale-110 transition-transform">
            <Target size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Active Projects</h3>
          {loading
            ? <Skeleton className="w-36 h-4 mt-1" />
            : <p className="text-xs text-slate-500 mt-1">
                {activeProjects !== undefined
                  ? `${String(activeProjects).padStart(2, '0')} Live Estimations`
                  : `${String(recentEstimates.length).padStart(2, '0')} Live Estimations`}
              </p>
          }
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 group hover:border-emerald-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center text-emerald-600 mb-4 group-hover:scale-110 transition-transform">
            <TrendingUp size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Direct Cost Pool</h3>
          <p className="text-xs text-slate-500 mt-1">AED 1.2M Overhead</p>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 group hover:border-amber-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center text-amber-600 mb-4 group-hover:scale-110 transition-transform">
            <Zap size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Optimization Gain</h3>
          <p className="text-xs text-slate-500 mt-1">96.8% Efficiency</p>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 group hover:border-red-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center text-red-600 mb-4 group-hover:scale-110 transition-transform">
            <AlertCircle size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Pending Audits</h3>
          {loading
            ? <Skeleton className="w-36 h-4 mt-1" />
            : <p className="text-xs text-slate-500 mt-1">
                {rfis !== undefined ? `${String(rfis).padStart(2, '0')} Requires Review` : `${String(recentEstimates.filter(e => e.status === 'REVIEW_REQUIRED').length).padStart(2, '0')} Requires Review`}
              </p>
          }
        </div>
      </div>

      {/* KEY METRICS (VIBRANT CARDS) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Total Estimates */}
        <div className="bg-gradient-to-br from-blue-600 to-blue-800 p-8 rounded-[2rem] shadow-xl shadow-blue-600/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Total Estimates</h3>
            {loading
              ? <Skeleton className="w-20 h-12 bg-white/20" />
              : <p className="text-5xl font-mono font-black tracking-tighter">
                  {String(totalEstimates).padStart(2, '0')}
                </p>
            }
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              View All <ChevronRight size={12} />
            </div>
          </div>
          <Briefcase size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>

        {/* Factory Margin */}
        <div className="bg-gradient-to-br from-emerald-500 to-emerald-700 p-8 rounded-[2rem] shadow-xl shadow-emerald-500/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Factory Margin</h3>
            {loading
              ? <Skeleton className="w-20 h-12 bg-white/20" />
              : <p className="text-5xl font-mono font-black tracking-tighter">
                  {marginPct !== undefined ? `${marginPct}%` : '18%'}
                </p>
            }
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              View Margin Matrix <ChevronRight size={12} />
            </div>
          </div>
          <Target size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>

        {/* Technical RFIs */}
        <div className="bg-gradient-to-br from-red-500 to-red-700 p-8 rounded-[2rem] shadow-xl shadow-red-500/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Technical RFIs</h3>
            {loading
              ? <Skeleton className="w-20 h-12 bg-white/20" />
              : <p className="text-5xl font-mono font-black tracking-tighter">
                  {rfis !== undefined ? String(rfis).padStart(2, '0') : '00'}
                </p>
            }
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              Resolve Issues <ChevronRight size={12} />
            </div>
          </div>
          <ShieldCheck size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>

        {/* Optimization Gaps */}
        <div className="bg-gradient-to-br from-amber-500 to-amber-600 p-8 rounded-[2rem] shadow-xl shadow-amber-500/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Optimization Gaps</h3>
            {loading
              ? <Skeleton className="w-20 h-12 bg-white/20" />
              : <p className="text-5xl font-mono font-black tracking-tighter">
                  {gaps !== undefined ? String(gaps).padStart(2, '0') : '00'}
                </p>
            }
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              Review Gaps <ChevronRight size={12} />
            </div>
          </div>
          <Zap size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>
      </div>

      {/* FEATURED PROJECT — dynamic from API */}
      {featuredEstimate && (
        <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-2xl shadow-xl p-8 relative overflow-hidden">
          <div className="absolute inset-0 opacity-5"
            style={{
              backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
              backgroundSize: '32px 32px',
            }}
          />
          <Building2 size={200} className="absolute -bottom-8 -right-8 opacity-5 rotate-6" />

          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div className="flex items-start gap-5">
              <div className="w-14 h-14 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center shrink-0">
                <Building2 size={28} className="text-blue-400" />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-[9px] font-black uppercase tracking-[0.25em] text-blue-400">Featured_Project</span>
                  <span className={`px-2 py-0.5 text-[9px] font-black uppercase tracking-widest rounded border ${
                    featuredEstimate.status === 'REVIEW_REQUIRED'
                      ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                      : 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                  }`}>
                    {featuredEstimate.status.replace(/_/g, ' ')}
                  </span>
                  {isInternational && (
                    <span className="px-2 py-0.5 text-[9px] font-black uppercase tracking-widest rounded border bg-purple-500/20 text-purple-400 border-purple-500/30 flex items-center gap-1">
                      <Globe size={10} /> International
                    </span>
                  )}
                </div>
                <h2 className="text-2xl font-black text-white uppercase tracking-tighter">
                  {featuredEstimate.project_name || 'Unnamed Project'}
                </h2>
                <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
                  {featuredEstimate.client_name && (
                    <>
                      <span className="flex items-center gap-1.5"><Briefcase size={12} /> {featuredEstimate.client_name}</span>
                      <span className="w-1 h-1 bg-slate-600 rounded-full" />
                    </>
                  )}
                  {featuredEstimate.location && (
                    <>
                      <span className="flex items-center gap-1.5"><MapPin size={12} /> {featuredEstimate.location}{isInternational ? ' (International)' : ''}</span>
                      <span className="w-1 h-1 bg-slate-600 rounded-full" />
                    </>
                  )}
                  {featuredEstimate.progress_pct !== undefined && (
                    <span>Progress: {featuredEstimate.progress_pct}%</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-col lg:items-end gap-3 shrink-0">
              <div className="flex gap-2">
                <Link
                  href={`/estimate/${featuredEstimate.estimate_id}`}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-600/30 flex items-center gap-2"
                >
                  Open Estimate <ChevronRight size={14} />
                </Link>
                {featuredEstimate.status === 'REVIEW_REQUIRED' && (
                  <Link
                    href={`/estimate/${featuredEstimate.estimate_id}/approve`}
                    className="px-5 py-2.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/30 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2"
                  >
                    <ShieldCheck size={14} /> Approve
                  </Link>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* RECENT ESTIMATES */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-2 h-6 bg-emerald-500 rounded-full"></div>
            <h3 className="text-sm font-black uppercase tracking-widest text-slate-800 italic">
              Recent_Estimates
            </h3>
          </div>
          <Link
            href="/estimate/new"
            className="text-[10px] font-black uppercase tracking-widest text-blue-600 hover:text-blue-700 flex items-center gap-1 transition-colors"
          >
            New Estimation <ChevronRight size={12} />
          </Link>
        </div>

        <div className="divide-y divide-slate-100">
          {recentEstimates.length === 0 && !loading && (
            <div className="px-8 py-12 text-center text-slate-400">
              <Building2 size={48} className="mx-auto mb-4 opacity-30" />
              <p className="text-sm font-bold">No estimates yet</p>
              <p className="text-xs mt-1">Create your first estimation to get started.</p>
            </div>
          )}
          {loading && recentEstimates.length === 0 && (
            <div className="px-8 py-5">
              <Skeleton className="w-full h-12" />
            </div>
          )}
          {recentEstimates.map((est, idx) => {
            const statusClass = STATUS_COLORS[est.status] ?? 'bg-slate-100 text-slate-500 border-slate-200';
            const estLocation = est.location || '';
            const estIsIntl = estLocation && !estLocation.toLowerCase().includes('uae');
            return (
              <div
                key={est.estimate_id}
                className={`flex items-center justify-between px-8 py-5 hover:bg-blue-50/30 transition-colors ${idx > 0 ? 'opacity-70' : ''}`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${idx === 0 ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                    <Building2 size={18} />
                  </div>
                  <div>
                    <p className={`text-sm font-black uppercase tracking-tight ${idx === 0 ? 'text-blue-600' : 'text-slate-700'}`}>
                      {est.project_name || est.estimate_id.slice(0, 12)}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5 uppercase font-medium tracking-tight">
                      {est.client_name || 'Unknown Client'}{estIsIntl ? ` · ${estLocation} (International)` : estLocation ? ` · ${estLocation}` : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <span className={`px-3 py-1 text-[9px] font-black uppercase tracking-widest rounded-full border ${statusClass}`}>
                    {est.status.replace(/_/g, ' ')}
                  </span>
                  <Link
                    href={`/estimate/${est.estimate_id}`}
                    className="text-[10px] bg-slate-800 hover:bg-blue-600 text-white px-4 py-2 rounded-xl transition-all uppercase font-black tracking-widest shadow-lg shadow-blue-600/10"
                  >
                    Open
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* LIVE SYNC FOOTER */}
      <div className="flex justify-center">
        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          <Clock size={14} /> Last Sync: {lastSyncTime || '...'}
        </div>
      </div>
    </div>
  );
}
