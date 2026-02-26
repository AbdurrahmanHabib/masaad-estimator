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
  project_name?: string;
  client_name?: string;
  status: string;
  total_sell_price_aed?: number;
  created_at?: string;
}

// ─── Al Kabir Tower — authoritative showcase project ─────────────────────────

const AL_KABIR: RecentEstimate = {
  estimate_id: 'PRJ-KAB-001',
  project_name: 'Al Kabir Tower',
  client_name: 'BIR Mimarlik',
  status: 'REVIEW_REQUIRED',
  total_sell_price_aed: 8_300_000,
  created_at: new Date().toISOString(),
};

const STATUS_COLORS: Record<string, string> = {
  ESTIMATING: 'bg-blue-100 text-blue-700 border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-100 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  DISPATCHED: 'bg-purple-100 text-purple-700 border-purple-200',
  Completed: 'bg-slate-100 text-slate-500 border-slate-200',
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
  const [recentEstimates, setRecentEstimates] = React.useState<RecentEstimate[]>([AL_KABIR]);
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
          // Ensure Al Kabir always appears first as the primary showcase project
          const withoutKabir = data.filter(e => e.estimate_id !== 'PRJ-KAB-001');
          setRecentEstimates([AL_KABIR, ...withoutKabir]);
        }
      } catch {
        // Non-fatal — keep static Al Kabir entry
      }
    };

    fetchSummary();
    fetchRecentEstimates();
  }, []);

  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'Admin';

  const activeProjects = summary?.total_projects ?? summary?.active_processing;
  const totalEstimates = summary?.total_estimates;
  const marginPct = summary?.factory_margin_pct;
  const rfis = summary?.technical_rfis;
  const gaps = summary?.optimization_gaps;

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
                  : '04 Live Estimations'}
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
                {rfis !== undefined ? `${String(rfis).padStart(2, '0')} Requires Review` : '02 Requires Review'}
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
                  {totalEstimates !== undefined ? String(totalEstimates).padStart(2, '0') : '90'}
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
                  {marginPct !== undefined ? `${marginPct}%` : '24%'}
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
                  {rfis !== undefined ? String(rfis).padStart(2, '0') : '02'}
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
                  {gaps !== undefined ? String(gaps).padStart(2, '0') : '05'}
                </p>
            }
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              Review Gaps <ChevronRight size={12} />
            </div>
          </div>
          <Zap size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>
      </div>

      {/* AL KABIR TOWER — PRIMARY SHOWCASE PROJECT */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-2xl shadow-xl p-8 relative overflow-hidden">
        {/* Background decoration */}
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
                <span className="px-2 py-0.5 text-[9px] font-black uppercase tracking-widest rounded border bg-amber-500/20 text-amber-400 border-amber-500/30">
                  Review Required
                </span>
                <span className="px-2 py-0.5 text-[9px] font-black uppercase tracking-widest rounded border bg-purple-500/20 text-purple-400 border-purple-500/30 flex items-center gap-1">
                  <Globe size={10} /> International
                </span>
              </div>
              <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Al Kabir Tower</h2>
              <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><Briefcase size={12} /> BIR Mimarlik</span>
                <span className="w-1 h-1 bg-slate-600 rounded-full" />
                <span className="flex items-center gap-1.5"><MapPin size={12} /> Turkey (International)</span>
                <span className="w-1 h-1 bg-slate-600 rounded-full" />
                <span>15-Story Mixed-Use Tower</span>
                <span className="w-1 h-1 bg-slate-600 rounded-full" />
                <span>Curtain Wall · ACP · Balustrades · Spider Glazing</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col lg:items-end gap-3 shrink-0">
            <div className="flex items-baseline gap-2">
              <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Contract Value</span>
              <span className="text-3xl font-mono font-black text-white">AED 8.3M</span>
            </div>
            <div className="flex gap-2">
              <Link
                href="/estimate/PRJ-KAB-001"
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-600/30 flex items-center gap-2"
              >
                Open Estimate <ChevronRight size={14} />
              </Link>
              <Link
                href="/estimate/PRJ-KAB-001/approve"
                className="px-5 py-2.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/30 rounded-xl text-xs font-black uppercase tracking-widest transition-all flex items-center gap-2"
              >
                <ShieldCheck size={14} /> Approve
              </Link>
            </div>
          </div>
        </div>
      </div>

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
          {recentEstimates.map((est, idx) => {
            const isKabir = est.estimate_id === 'PRJ-KAB-001';
            const statusClass = STATUS_COLORS[est.status] ?? 'bg-slate-100 text-slate-500 border-slate-200';
            return (
              <div
                key={est.estimate_id}
                className={`flex items-center justify-between px-8 py-5 hover:bg-blue-50/30 transition-colors ${idx > 0 ? 'opacity-70' : ''}`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${isKabir ? 'bg-blue-50 text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                    <Building2 size={18} />
                  </div>
                  <div>
                    <p className={`text-sm font-black uppercase tracking-tight ${isKabir ? 'text-blue-600' : 'text-slate-700'}`}>
                      {est.project_name || est.estimate_id}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5 uppercase font-medium tracking-tight">
                      {est.client_name || 'Unknown Client'} {isKabir ? '· Turkey (International)' : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  {est.total_sell_price_aed && (
                    <span className="text-sm font-mono font-black text-slate-800">
                      AED {(est.total_sell_price_aed / 1_000_000).toFixed(1)}M
                    </span>
                  )}
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

      {/* PROJECT DEPLOYMENT QUEUE */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-2 h-6 bg-blue-600 rounded-full"></div>
            <h3 className="text-sm font-black uppercase tracking-widest text-slate-800 italic">
              Project_Deployment_Queue
            </h3>
          </div>
          <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            <Clock size={14} /> Last Sync: {lastSyncTime || '...'}
          </div>
        </div>

        <table className="w-full text-left">
          <thead className="bg-slate-50 text-slate-400 uppercase text-[9px] font-black tracking-widest border-b border-slate-200">
            <tr>
              <th className="px-8 py-4">Project_Ref</th>
              <th className="px-8 py-4">Primary_Client</th>
              <th className="px-8 py-4">Region</th>
              <th className="px-8 py-4">Status</th>
              <th className="px-8 py-4 text-right">Verification</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-sans text-xs">
            {loading ? (
              // Skeleton rows while loading
              [1, 2].map((i) => (
                <tr key={i}>
                  <td className="px-8 py-5"><Skeleton className="w-28 h-4" /></td>
                  <td className="px-8 py-5"><Skeleton className="w-36 h-4" /></td>
                  <td className="px-8 py-5"><Skeleton className="w-28 h-4" /></td>
                  <td className="px-8 py-5"><Skeleton className="w-24 h-6 rounded-full" /></td>
                  <td className="px-8 py-5 text-right"><Skeleton className="w-24 h-8 ml-auto rounded-xl" /></td>
                </tr>
              ))
            ) : summary?.projects && summary.projects.length > 0 ? (
              summary.projects.map((project, idx) => (
                <tr
                  key={project.project_ref}
                  className={`hover:bg-blue-50/30 transition-colors group ${idx > 0 ? 'opacity-60' : ''}`}
                >
                  <td className="px-8 py-5 font-black text-blue-600">{project.project_ref}</td>
                  <td className="px-8 py-5 text-slate-700 font-bold uppercase tracking-tight italic">{project.client_name}</td>
                  <td className="px-8 py-5 text-slate-500 uppercase text-[10px] font-medium tracking-tighter">{project.region}</td>
                  <td className="px-8 py-5">
                    <span className={`px-3 py-1 text-[9px] font-black uppercase tracking-widest rounded-full shadow-sm border ${
                      project.status.toLowerCase().includes('complet')
                        ? 'bg-slate-100 text-slate-400 border-slate-200'
                        : 'bg-emerald-100 text-emerald-600 border-emerald-200'
                    }`}>
                      {project.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-8 py-5 text-right">
                    {project.status.toLowerCase().includes('complet') ? (
                      <button className="text-[10px] text-slate-400 font-black uppercase tracking-widest cursor-not-allowed">
                        Archive_Only
                      </button>
                    ) : (
                      <Link
                        href={`/estimate/${project.project_ref}`}
                        className="text-[10px] bg-slate-800 hover:bg-blue-600 text-white px-5 py-2 rounded-xl transition-all uppercase font-black tracking-widest shadow-lg shadow-blue-600/10"
                      >
                        Launch_Audit
                      </Link>
                    )}
                  </td>
                </tr>
              ))
            ) : (
              // Static fallback rows when API returns no projects
              <>
                <tr className="hover:bg-blue-50/30 transition-colors group">
                  <td className="px-8 py-5 font-black text-blue-600">PRJ-KAB-001</td>
                  <td className="px-8 py-5 text-slate-700 font-bold uppercase tracking-tight italic">Al Kabir Tower</td>
                  <td className="px-8 py-5 text-slate-500 uppercase text-[10px] font-medium tracking-tighter">Turkey_(International)</td>
                  <td className="px-8 py-5">
                    <span className="px-3 py-1 bg-amber-100 text-amber-700 border border-amber-200 text-[9px] font-black uppercase tracking-widest rounded-full shadow-sm">
                      Review_Required
                    </span>
                  </td>
                  <td className="px-8 py-5 text-right">
                    <Link
                      href="/estimate/PRJ-KAB-001"
                      className="text-[10px] bg-slate-800 hover:bg-blue-600 text-white px-5 py-2 rounded-xl transition-all uppercase font-black tracking-widest shadow-lg shadow-blue-600/10"
                    >
                      Launch_Audit
                    </Link>
                  </td>
                </tr>
                <tr className="hover:bg-blue-50/30 transition-colors opacity-60">
                  <td className="px-8 py-5 text-slate-400">PRJ-DXB-042</td>
                  <td className="px-8 py-5 text-slate-400 font-bold uppercase tracking-tight italic">Dubai Hills Villa</td>
                  <td className="px-8 py-5 text-slate-400 uppercase text-[10px] font-medium">Dubai_UAE</td>
                  <td className="px-8 py-5">
                    <span className="px-3 py-1 bg-slate-100 text-slate-400 text-[9px] font-bold uppercase tracking-widest rounded-full">
                      Completed
                    </span>
                  </td>
                  <td className="px-8 py-5 text-right">
                    <button className="text-[10px] text-slate-400 font-black uppercase tracking-widest cursor-not-allowed">
                      Archive_Only
                    </button>
                  </td>
                </tr>
              </>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
