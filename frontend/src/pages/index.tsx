import React from 'react';
import Link from 'next/link';
import {
  Briefcase,
  TrendingUp,
  Clock,
  ChevronRight,
  ChevronDown,
  AlertCircle,
  MapPin,
  Building2,
  Plus,
  FileText,
  Loader2,
  Trash2,
  Download,
  Shield,
  Scissors,
  Package,
  Layers,
  BarChart3,
  AlertTriangle,
  Lightbulb,
  Eye,
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { apiGet, apiDelete, apiFetch } from '../lib/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface SystemBreakdown {
  system_type: string;
  category: string;
  count: number;
  area: number;
  unit: string;
  color: string;
}

interface CategoryTotal {
  count: number;
  area: number;
  color: string;
}

interface DashboardSummary {
  total_projects: number;
  total_estimates: number;
  active_processing: number;
  pending_review: number;
  total_facade_sqm: number;
  total_openings: number;
  total_contract_value_aed: number;
  systems_breakdown: SystemBreakdown[];
  category_totals: Record<string, CategoryTotal>;
  floors_breakdown: Record<string, number>;
  elevations_breakdown: Record<string, number>;
  materials_summary: {
    aluminum_kg: number;
    glass_sqm: number;
    total_weight_kg: number;
    truck_loads: number;
  };
  engineering_summary: {
    total_checks: number;
    pass: number;
    fail: number;
    warning: number;
    compliance_pct: number;
  };
  cutting_summary: {
    profiles: number;
    bars_required: number;
    avg_yield_pct: number;
  };
  financial_totals: {
    material_aed: number;
    labor_aed: number;
    overhead_aed: number;
    grand_total_aed: number;
  };
  rfi_summary: {
    total: number;
    by_severity: Record<string, number>;
  };
  ve_summary: {
    opportunities: number;
    savings_aed: number;
  };
}

interface OpeningItem {
  opening_id?: string;
  mark_id?: string;
  item_code?: string;
  system_type?: string;
  width_mm?: number;
  height_mm?: number;
  qty?: number;
  count?: number;
  gross_area_sqm?: number;
  net_glazed_sqm?: number;
  floor?: string;
  elevation?: string;
  glass_type?: string;
  aluminum_weight_kg?: number;
  gasket_length_lm?: number;
  hardware_sets?: number;
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
  created_at?: string;
  updated_at?: string;
  scope?: {
    facade_sqm: number;
    systems_count: number;
    systems_list: { system_type: string; total_sqm: number; total_openings: number }[];
    confidence: string;
  };
  openings?: {
    items: OpeningItem[];
    total_openings: number;
    by_type: Record<string, number>;
    by_floor: Record<string, number>;
    by_elevation: Record<string, number>;
    floor_count: number;
  };
  materials?: {
    aluminum_kg: number;
    glass_sqm: number;
    total_weight_kg: number;
    truck_loads: number;
    bom_items: number;
  };
  cutting?: { profiles: number; bars_required: number; avg_yield_pct: number };
  engineering?: { total_checks: number; pass: number; fail: number; warning: number; compliance_pct: number };
  financial?: { material_aed: number; labor_aed: number; overhead_aed: number; total_aed: number };
  rfis?: { total: number; by_severity: Record<string, number> };
  ve?: { opportunities: number; savings_aed: number };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, string> = {
  ESTIMATING: 'bg-blue-50 text-[#002147] border-blue-200',
  Processing: 'bg-blue-50 text-[#002147] border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  DISPATCHED: 'bg-purple-50 text-purple-700 border-purple-200',
  Completed: 'bg-slate-50 text-[#64748b] border-slate-200',
  Queued: 'bg-blue-50 text-[#002147] border-blue-200',
  Failed: 'bg-red-50 text-red-600 border-red-200',
};

function fmt(n: number | undefined, dec = 0): string {
  if (n === undefined || n === null) return '0';
  return n.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function fmtAED(n: number | undefined): string {
  if (!n) return 'AED 0';
  return `AED ${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ── Components ───────────────────────────────────────────────────────────────

function KPICard({ label, value, icon: Icon, borderColor, loading }: {
  label: string; value: string | number; icon: any; borderColor: string; loading: boolean;
}) {
  return (
    <div className={`bg-white border border-[#e2e8f0] border-l-4 ${borderColor} rounded-md p-5 shadow-sm`}>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={15} className="text-[#64748b]" />
        <span className="text-[11px] font-medium text-[#64748b] uppercase tracking-wider">{label}</span>
      </div>
      {loading ? (
        <div className="h-7 bg-slate-100 rounded animate-pulse w-16" />
      ) : (
        <p className="text-xl font-bold text-[#1e293b] font-mono">{value}</p>
      )}
    </div>
  );
}

function SectionHeader({ title, icon: Icon }: { title: string; icon: any }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <Icon size={16} className="text-[#64748b]" />
      <h3 className="text-sm font-semibold text-[#1e293b]">{title}</h3>
    </div>
  );
}

function BarRow({ label, value, maxValue, color, suffix = '' }: {
  label: string; value: number; maxValue: number; color: string; suffix?: string;
}) {
  const pct = maxValue > 0 ? Math.min((value / maxValue) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-3 py-1.5">
      <span className="text-xs text-[#64748b] w-12 shrink-0 text-right font-mono">{label}</span>
      <div className="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono text-[#1e293b] w-20 text-right">{fmt(value, 1)}{suffix}</span>
    </div>
  );
}

function OpeningScheduleTable({ items }: { items: OpeningItem[] }) {
  if (!items || items.length === 0) {
    return <p className="text-xs text-[#94a3b8] py-2 px-4">No opening data available</p>;
  }

  // Sort by floor then system type
  const sorted = [...items].sort((a, b) => {
    const fa = a.floor || '';
    const fb = b.floor || '';
    if (fa !== fb) return fa.localeCompare(fb);
    return (a.system_type || '').localeCompare(b.system_type || '');
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-slate-100">
            <th className="text-left py-2 px-3 font-medium text-[#64748b]">Item Code</th>
            <th className="text-left py-2 px-3 font-medium text-[#64748b]">System Type</th>
            <th className="text-right py-2 px-3 font-medium text-[#64748b]">W (mm)</th>
            <th className="text-right py-2 px-3 font-medium text-[#64748b]">H (mm)</th>
            <th className="text-right py-2 px-3 font-medium text-[#64748b]">Qty</th>
            <th className="text-right py-2 px-3 font-medium text-[#64748b]">Area SQM</th>
            <th className="text-left py-2 px-3 font-medium text-[#64748b]">Floor</th>
            <th className="text-left py-2 px-3 font-medium text-[#64748b]">Elevation</th>
            <th className="text-left py-2 px-3 font-medium text-[#64748b]">Glass</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {sorted.map((item, i) => (
            <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
              <td className="py-1.5 px-3 font-mono text-[#002147]">{item.item_code || item.mark_id || '--'}</td>
              <td className="py-1.5 px-3">{item.system_type || '--'}</td>
              <td className="py-1.5 px-3 text-right font-mono">{fmt(item.width_mm)}</td>
              <td className="py-1.5 px-3 text-right font-mono">{fmt(item.height_mm)}</td>
              <td className="py-1.5 px-3 text-right font-mono">{item.qty || item.count || 1}</td>
              <td className="py-1.5 px-3 text-right font-mono">{fmt(item.gross_area_sqm, 2)}</td>
              <td className="py-1.5 px-3">{item.floor || '--'}</td>
              <td className="py-1.5 px-3">{item.elevation || '--'}</td>
              <td className="py-1.5 px-3 text-[#64748b]">{item.glass_type || '--'}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-slate-100 font-medium">
            <td className="py-2 px-3" colSpan={4}>Totals</td>
            <td className="py-2 px-3 text-right font-mono">{fmt(sorted.reduce((s, i) => s + (i.qty || i.count || 1), 0))}</td>
            <td className="py-2 px-3 text-right font-mono">{fmt(sorted.reduce((s, i) => s + (i.gross_area_sqm || 0), 0), 2)}</td>
            <td colSpan={3}></td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

// ── Main Dashboard ───────────────────────────────────────────────────────────

export default function Dashboard() {
  const { user } = useAuthStore();
  const [summary, setSummary] = React.useState<DashboardSummary | null>(null);
  const [recentEstimates, setRecentEstimates] = React.useState<RecentEstimate[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [expandedRows, setExpandedRows] = React.useState<Set<string>>(new Set());
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

  const toggleRow = (id: string) => {
    setExpandedRows(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleExport = async (type: 'excel' | 'pdf') => {
    try {
      const resp = await apiFetch(`/api/dashboard/export/${type}`);
      if (!resp.ok) throw new Error('Export failed');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = type === 'excel' ? 'masaad_dashboard_report.xlsx' : 'masaad_dashboard_summary.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Export failed');
    }
  };

  const handleEstimateDownload = async (estimateId: string, format: 'pdf' | 'excel' | 'drawings') => {
    try {
      const path = format === 'drawings'
        ? `/api/reports/estimate/${estimateId}/drawings`
        : `/api/reports/estimate/${estimateId}/${format}`;
      const resp = await apiFetch(path);
      if (!resp.ok) throw new Error(`${format} download failed`);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `estimate_${estimateId.slice(0, 8)}.${format === 'excel' ? 'xlsx' : format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Download failed');
    }
  };

  const firstName = user?.full_name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'Admin';
  const s = summary;
  const hasData = s && (s.total_estimates > 0 || recentEstimates.length > 0);

  // Find max values for bar charts
  const maxFloorSqm = s ? Math.max(...Object.values(s.floors_breakdown || {}), 1) : 1;
  const maxElevSqm = s ? Math.max(...Object.values(s.elevations_breakdown || {}), 1) : 1;

  return (
    <div className="space-y-5">
      {/* WELCOME BANNER */}
      <div className="bg-gradient-to-r from-[#002147] to-[#1e3a5f] rounded-md p-5 flex flex-col sm:flex-row justify-between sm:items-end gap-4">
        <div>
          <h1 className="text-lg font-bold text-white">Welcome back, {firstName}</h1>
          <p className="text-white/60 text-xs mt-1">Facade Intelligence Dashboard</p>
        </div>
        <Link
          href="/estimate/new"
          className="px-4 py-2 bg-[#002147] hover:bg-[#1e3a5f] border border-white/20 text-white rounded-md text-sm font-medium transition-all flex items-center gap-2 shrink-0"
        >
          <Plus size={15} /> New Estimation
        </Link>
      </div>

      {/* SECTION A: KPI CARDS */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KPICard label="Projects" value={s?.total_projects ?? 0} icon={Briefcase} borderColor="border-l-[#3b82f6]" loading={loading} />
        <KPICard label="Estimates" value={s?.total_estimates ?? 0} icon={FileText} borderColor="border-l-[#059669]" loading={loading} />
        <KPICard label="Pending Review" value={s?.pending_review ?? 0} icon={AlertCircle} borderColor="border-l-[#d97706]" loading={loading} />
        <KPICard label="Facade SQM" value={fmt(s?.total_facade_sqm, 1)} icon={Layers} borderColor="border-l-[#0891b2]" loading={loading} />
        <KPICard label="Openings" value={fmt(s?.total_openings)} icon={Building2} borderColor="border-l-[#7c3aed]" loading={loading} />
        <KPICard label="Pipeline AED" value={fmt(s?.total_contract_value_aed, 0)} icon={TrendingUp} borderColor="border-l-[#002147]" loading={loading} />
      </div>

      {/* Only show detail sections if there's data */}
      {hasData && (
        <>
          {/* SECTION B: FACADE SYSTEMS */}
          {s && Object.keys(s.category_totals || {}).length > 0 && (
            <div className="bg-white border border-[#e2e8f0] rounded-md p-5 shadow-sm">
              <SectionHeader title="Facade Systems Breakdown" icon={Layers} />
              <div className="space-y-4">
                {Object.entries(s.category_totals).map(([cat, totals]) => {
                  const systems = s.systems_breakdown.filter(sb => sb.category === cat);
                  return (
                    <div key={cat}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: totals.color }} />
                        <span className="text-xs font-semibold text-[#1e293b]">{cat}</span>
                        <span className="text-[10px] text-[#94a3b8] ml-auto">{totals.count} items | {fmt(totals.area, 1)} sqm</span>
                      </div>
                      <div className="pl-5 space-y-0.5">
                        {systems.map(sys => (
                          <div key={sys.system_type} className="flex items-center gap-2 text-xs">
                            <span className="text-[#64748b] w-48 truncate">{sys.system_type}</span>
                            <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${Math.min((sys.count / Math.max(totals.count, 1)) * 100, 100)}%`,
                                  backgroundColor: sys.color,
                                  opacity: 0.7,
                                }}
                              />
                            </div>
                            <span className="font-mono text-[#1e293b] w-16 text-right">{sys.count}</span>
                            <span className="font-mono text-[#94a3b8] w-20 text-right">{fmt(sys.area, 1)} {sys.unit}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* SECTION C: BUILDING + MATERIALS */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Floors & Elevations */}
            {s && (Object.keys(s.floors_breakdown || {}).length > 0 || Object.keys(s.elevations_breakdown || {}).length > 0) && (
              <div className="bg-white border border-[#e2e8f0] rounded-md p-5 shadow-sm">
                <SectionHeader title="Building Analysis" icon={Building2} />
                {Object.keys(s.floors_breakdown || {}).length > 0 && (
                  <div className="mb-4">
                    <p className="text-[10px] font-semibold text-[#94a3b8] uppercase tracking-wider mb-1">Floors</p>
                    {Object.entries(s.floors_breakdown).map(([floor, sqm]) => (
                      <BarRow key={floor} label={floor} value={sqm} maxValue={maxFloorSqm} color="#3b82f6" suffix=" sqm" />
                    ))}
                  </div>
                )}
                {Object.keys(s.elevations_breakdown || {}).length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-[#94a3b8] uppercase tracking-wider mb-1">Elevations</p>
                    {Object.entries(s.elevations_breakdown).map(([elev, sqm]) => (
                      <BarRow key={elev} label={elev} value={sqm} maxValue={maxElevSqm} color="#7c3aed" suffix=" sqm" />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Materials */}
            {s && s.materials_summary && (
              <div className="bg-white border border-[#e2e8f0] rounded-md p-5 shadow-sm">
                <SectionHeader title="Materials Summary" icon={Package} />
                <div className="space-y-3">
                  {[
                    { label: 'Aluminum', value: s.materials_summary.aluminum_kg, unit: 'kg', color: '#64748b' },
                    { label: 'Glass', value: s.materials_summary.glass_sqm, unit: 'sqm', color: '#0891b2' },
                    { label: 'Total Weight', value: s.materials_summary.total_weight_kg, unit: 'kg', color: '#1e293b' },
                  ].map(m => (
                    <div key={m.label} className="flex justify-between items-center py-2 border-b border-slate-100 last:border-0">
                      <span className="text-xs text-[#64748b]">{m.label}</span>
                      <span className="text-sm font-mono font-semibold" style={{ color: m.color }}>{fmt(m.value, 1)} {m.unit}</span>
                    </div>
                  ))}
                  <div className="flex justify-between items-center pt-1">
                    <span className="text-xs text-[#64748b]">Truck Loads (20T)</span>
                    <span className="text-sm font-mono font-semibold text-[#d97706]">{s.materials_summary.truck_loads}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* SECTION D: ENGINEERING + FINANCIAL */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {s && s.engineering_summary && s.engineering_summary.total_checks > 0 && (
              <div className="bg-white border border-[#e2e8f0] rounded-md p-5 shadow-sm">
                <SectionHeader title="Engineering Compliance" icon={Shield} />
                <div className="flex items-center gap-4 mb-3">
                  <div className="text-3xl font-bold font-mono text-[#1e293b]">{s.engineering_summary.compliance_pct}%</div>
                  <div className="text-xs text-[#64748b]">{s.engineering_summary.total_checks} checks</div>
                </div>
                <div className="flex gap-2">
                  {[
                    { label: 'Pass', count: s.engineering_summary.pass, color: 'bg-emerald-100 text-emerald-700' },
                    { label: 'Fail', count: s.engineering_summary.fail, color: 'bg-red-100 text-red-700' },
                    { label: 'Warning', count: s.engineering_summary.warning, color: 'bg-amber-100 text-amber-700' },
                  ].map(x => (
                    <span key={x.label} className={`px-2 py-1 rounded text-xs font-medium ${x.color}`}>
                      {x.label}: {x.count}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {s && s.financial_totals && s.financial_totals.grand_total_aed > 0 && (
              <div className="bg-white border border-[#e2e8f0] rounded-md p-5 shadow-sm">
                <SectionHeader title="Financial Summary" icon={TrendingUp} />
                <div className="space-y-2">
                  {[
                    { label: 'Material', value: s.financial_totals.material_aed, color: '#3b82f6' },
                    { label: 'Labor', value: s.financial_totals.labor_aed, color: '#059669' },
                    { label: 'Overhead', value: s.financial_totals.overhead_aed, color: '#d97706' },
                  ].map(item => (
                    <div key={item.label} className="flex justify-between items-center py-1.5 border-b border-slate-100">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: item.color }} />
                        <span className="text-xs text-[#64748b]">{item.label}</span>
                      </div>
                      <span className="text-xs font-mono text-[#1e293b]">{fmtAED(item.value)}</span>
                    </div>
                  ))}
                  <div className="flex justify-between items-center pt-2">
                    <span className="text-xs font-semibold text-[#1e293b]">Grand Total</span>
                    <span className="text-sm font-mono font-bold text-[#002147]">{fmtAED(s.financial_totals.grand_total_aed)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* SECTION E: RFIs + VE */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {s && s.rfi_summary && s.rfi_summary.total > 0 && (
              <div className="bg-white border border-[#e2e8f0] rounded-md p-5 shadow-sm">
                <SectionHeader title="RFI Register" icon={AlertTriangle} />
                <div className="flex items-center gap-4 mb-3">
                  <div className="text-2xl font-bold font-mono text-[#1e293b]">{s.rfi_summary.total}</div>
                  <span className="text-xs text-[#64748b]">total RFIs</span>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(s.rfi_summary.by_severity).map(([sev, cnt]) => (
                    <span key={sev} className={`px-2 py-1 rounded text-xs font-medium ${
                      sev === 'HIGH' ? 'bg-red-100 text-red-700' :
                      sev === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {sev}: {cnt}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {s && s.ve_summary && s.ve_summary.opportunities > 0 && (
              <div className="bg-white border border-[#e2e8f0] rounded-md p-5 shadow-sm">
                <SectionHeader title="Value Engineering" icon={Lightbulb} />
                <div className="flex items-center gap-4 mb-2">
                  <div className="text-2xl font-bold font-mono text-[#059669]">{s.ve_summary.opportunities}</div>
                  <span className="text-xs text-[#64748b]">opportunities identified</span>
                </div>
                <p className="text-sm font-mono text-[#002147]">Potential Savings: {fmtAED(s.ve_summary.savings_aed)}</p>
              </div>
            )}
          </div>

          {/* SECTION F: CUTTING LIST */}
          {s && s.cutting_summary && s.cutting_summary.profiles > 0 && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: 'Profiles', value: s.cutting_summary.profiles, icon: Scissors },
                { label: 'Bars Required', value: s.cutting_summary.bars_required, icon: BarChart3 },
                { label: 'Avg Yield', value: `${s.cutting_summary.avg_yield_pct}%`, icon: TrendingUp },
              ].map(card => (
                <div key={card.label} className="bg-white border border-[#e2e8f0] rounded-md p-4 shadow-sm text-center">
                  <card.icon size={18} className="mx-auto mb-2 text-[#64748b]" />
                  <p className="text-lg font-bold font-mono text-[#1e293b]">{card.value}</p>
                  <p className="text-[10px] text-[#94a3b8] uppercase tracking-wider mt-1">{card.label}</p>
                </div>
              ))}
            </div>
          )}

          {/* SECTION G: DOWNLOAD BUTTONS */}
          <div className="flex gap-3">
            <button
              onClick={() => handleExport('excel')}
              className="px-4 py-2 bg-[#059669] hover:bg-[#047857] text-white rounded-md text-sm font-medium flex items-center gap-2 transition-colors"
            >
              <Download size={15} /> Excel Report
            </button>
            <button
              onClick={() => handleExport('pdf')}
              className="px-4 py-2 bg-[#002147] hover:bg-[#1e3a5f] text-white rounded-md text-sm font-medium flex items-center gap-2 transition-colors"
            >
              <Download size={15} /> PDF Summary
            </button>
          </div>
        </>
      )}

      {/* SECTION H: ESTIMATES TABLE */}
      <div className="bg-white border border-[#e2e8f0] rounded-md overflow-hidden shadow-sm">
        <div className="px-5 py-3 border-b border-[#e2e8f0] flex justify-between items-center">
          <h3 className="text-sm font-semibold text-[#1e293b]">Estimates</h3>
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
            <p className="text-xs mt-1">Upload drawings to start your first facade estimation.</p>
            <Link
              href="/estimate/new"
              className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-[#002147] text-white rounded-md text-sm font-medium hover:bg-[#1e3a5f] transition-colors"
            >
              <Plus size={14} /> Start Estimation
            </Link>
          </div>
        )}

        {recentEstimates.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-[#002147]">
                  <th className="text-left py-2.5 px-4 font-semibold text-white uppercase tracking-wider"></th>
                  <th className="text-left py-2.5 px-4 font-semibold text-white uppercase tracking-wider">Project</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Systems</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Openings</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Floors</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-white uppercase tracking-wider">SQM</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Weight</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Value</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Compliance</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-white uppercase tracking-wider">RFIs</th>
                  <th className="text-center py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Status</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-white uppercase tracking-wider">Progress</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white uppercase tracking-wider"></th>
                </tr>
              </thead>
              <tbody>
                {recentEstimates.map((est, idx) => {
                  const statusStyle = STATUS_STYLES[est.status] ?? 'bg-slate-50 text-[#64748b] border-slate-200';
                  const isExpanded = expandedRows.has(est.estimate_id);
                  return (
                    <React.Fragment key={est.estimate_id}>
                      <tr
                        className={`${idx % 2 === 1 ? 'bg-slate-50/50' : 'bg-white'} hover:bg-blue-50/30 cursor-pointer transition-colors`}
                        onClick={() => toggleRow(est.estimate_id)}
                      >
                        <td className="py-2.5 px-4">
                          {isExpanded ? <ChevronDown size={14} className="text-[#64748b]" /> : <ChevronRight size={14} className="text-[#94a3b8]" />}
                        </td>
                        <td className="py-2.5 px-4">
                          <p className="font-medium text-[#1e293b]">{est.project_name || est.estimate_id.slice(0, 12)}</p>
                          {est.client_name && <p className="text-[10px] text-[#94a3b8]">{est.client_name}</p>}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono">{est.scope?.systems_count ?? '--'}</td>
                        <td className="py-2.5 px-3 text-center font-mono">{est.openings?.total_openings ?? '--'}</td>
                        <td className="py-2.5 px-3 text-center font-mono">{est.openings?.floor_count ?? '--'}</td>
                        <td className="py-2.5 px-3 text-right font-mono">{fmt(est.scope?.facade_sqm, 1)}</td>
                        <td className="py-2.5 px-3 text-right font-mono text-[#64748b]">{est.materials?.total_weight_kg ? `${fmt(est.materials.total_weight_kg, 0)} kg` : '--'}</td>
                        <td className="py-2.5 px-3 text-right font-mono">{est.financial?.total_aed ? fmtAED(est.financial.total_aed) : '--'}</td>
                        <td className="py-2.5 px-3 text-center">
                          {est.engineering?.compliance_pct !== undefined ? (
                            <span className={`text-xs font-mono font-medium ${est.engineering.compliance_pct >= 90 ? 'text-emerald-600' : est.engineering.compliance_pct >= 70 ? 'text-amber-600' : 'text-red-600'}`}>
                              {est.engineering.compliance_pct}%
                            </span>
                          ) : '--'}
                        </td>
                        <td className="py-2.5 px-3 text-center font-mono">{est.rfis?.total ?? '--'}</td>
                        <td className="py-2.5 px-3 text-center">
                          <span className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded border ${statusStyle}`}>
                            {est.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-[#1e293b]">
                          {est.progress_pct !== undefined ? `${est.progress_pct}%` : '--'}
                        </td>
                        <td className="py-2.5 px-4 text-right" onClick={e => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              href={`/estimate/${est.estimate_id}`}
                              className="text-[#002147] hover:text-[#1e3a5f] transition-colors"
                              title="View details"
                            >
                              <Eye size={14} />
                            </Link>
                            <button
                              onClick={() => handleDelete(est.estimate_id, est.project_name)}
                              className="p-0.5 text-[#94a3b8] hover:text-red-500 transition-colors rounded hover:bg-red-50"
                              title="Delete"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Expanded row: Opening Schedule + Downloads */}
                      {isExpanded && (
                        <tr>
                          <td colSpan={13} className="bg-slate-50 border-t border-b border-[#e2e8f0]">
                            <div className="p-4">
                              <div className="flex items-center justify-between mb-3">
                                <h4 className="text-xs font-semibold text-[#1e293b]">Opening Schedule</h4>
                                <div className="flex gap-2">
                                  <button
                                    onClick={() => handleEstimateDownload(est.estimate_id, 'pdf')}
                                    className="px-3 py-1 bg-[#002147] text-white rounded text-[10px] font-medium hover:bg-[#1e3a5f] transition-colors flex items-center gap-1"
                                  >
                                    <Download size={11} /> PDF
                                  </button>
                                  <button
                                    onClick={() => handleEstimateDownload(est.estimate_id, 'excel')}
                                    className="px-3 py-1 bg-[#059669] text-white rounded text-[10px] font-medium hover:bg-[#047857] transition-colors flex items-center gap-1"
                                  >
                                    <Download size={11} /> Excel
                                  </button>
                                  <button
                                    onClick={() => handleEstimateDownload(est.estimate_id, 'drawings')}
                                    className="px-3 py-1 bg-[#7c3aed] text-white rounded text-[10px] font-medium hover:bg-[#6d28d9] transition-colors flex items-center gap-1"
                                  >
                                    <Download size={11} /> Drawings
                                  </button>
                                </div>
                              </div>
                              <OpeningScheduleTable items={est.openings?.items || []} />
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
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
