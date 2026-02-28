import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  Layers,
  DollarSign,
  ShieldAlert,
  TrendingUp,
  Briefcase,
  MapPin,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ChevronRight,
  Download,
  Printer,
  Loader2,
  ArrowLeft,
  Package,
  ClipboardList,
  BarChart3,
  ShieldCheck,
  ListChecks,
  Wrench,
  Ruler,
  Grid3X3,
  Scissors,
} from 'lucide-react';
import { apiGet, apiPost, apiFetch } from '../../lib/api';

// Types

interface SSEProgress {
  estimate_id: string;
  current_agent: string;
  status_message: string;
  confidence_score: number;
  progress_pct: number;
  partial_results?: {
    status?: string;
    bom_rows?: number;
  };
  hitl_required?: boolean;
  hitl_triage_id?: string | null;
  error?: string | null;
}

interface BOMItem {
  item_code?: string;
  description?: string;
  category?: string;
  quantity?: number;
  unit?: string;
  unit_rate?: number;
  subtotal_aed?: number;
  notes?: string;
}

interface FinancialSummary {
  total_aed?: number;
  material_cost_aed?: number;
  labor_cost_aed?: number;
  gross_margin_pct?: number;
  overhead_aed?: number;
  margin_aed?: number;
  attic_stock_cost_aed?: number;
  provisional_sums_aed?: number;
  retention_pct?: number;
  factory_overhead_aed?: number;
  project_management_aed?: number;
  design_fee_aed?: number;
  insurance_aed?: number;
  warranty_aed?: number;
  vat_aed?: number;
  total_incl_vat_aed?: number;
  [key: string]: unknown;
}

interface OpeningItem {
  opening_id?: string;
  id?: string;
  mark_id?: string;
  type?: string;
  opening_type?: string;
  width?: number;
  width_mm?: number;
  height?: number;
  height_mm?: number;
  area?: number;
  area_sqm?: number;
  glass_area?: number;
  glass_area_sqm?: number;
  system_type?: string;
  system?: string;
  quantity?: number;
  qty?: number;
  floor?: string | number;
  [key: string]: unknown;
}

interface EstimateDetail {
  estimate_id: string;
  project_id?: string;
  project_name?: string;
  client_name?: string;
  location?: string;
  status: string;
  progress_pct: number;
  current_step?: string;
  reasoning_log: string[];
  project_scope: Record<string, unknown>;
  opening_schedule: Record<string, unknown> | OpeningItem[];
  bom_output: {
    items?: BOMItem[];
    summary?: Record<string, unknown>;
  };
  cutting_list: Record<string, unknown>;
  boq: {
    summary?: {
      total_sell_price_aed?: number;
      total_direct_cost_aed?: number;
      gross_margin_pct?: number;
      total_weight_kg?: number;
    };
    line_items?: Array<{
      system_type?: string;
      item_code?: string;
      description?: string;
      quantity?: number;
      unit?: string;
      unit_rate_aed?: number;
      total_aed?: number;
    }>;
    financial_rates?: {
      lme_aluminum_usd_mt?: number;
      usd_aed_rate?: number;
      baseline_labor_burn_rate_aed?: number;
    };
  };
  rfi_register: Array<{
    rfi_id?: string;
    rfi_code?: string;
    question?: string;
    status?: string;
  }>;
  ve_opportunities: Array<{
    item_code?: string;
    description?: string;
    saving_aed?: number;
  }>;
  structural_results: Array<{
    system_type?: string;
    pass?: boolean;
    deflection_mm?: number;
    wind_load_kpa?: number;
    thermal_u_value?: number;
    acoustic_rw?: number;
  }>;
  financial_summary: FinancialSummary;
  engineering_results?: {
    summary?: { total_checks: number; pass: number; fail: number; warning: number; compliance_pct: number };
    wind_load_analysis?: Array<{ opening_id: string; check: string; wind_pressure_pa: number; safety_factor: number; status: string }>;
    thermal_analysis?: Array<{ opening_id: string; u_value_w_m2k: number; target_u_value: number; status: string }>;
    deflection_checks?: Array<{ opening_id: string; deflection_mm: number; allowable_mm: number; status: string }>;
    glass_stress_checks?: Array<{ opening_id: string; applied_stress_mpa: number; allowable_stress_mpa: number; status: string }>;
  };
  state_snapshot?: Record<string, unknown>;
}

// Helpers

const STATUS_STYLES: Record<string, string> = {
  ESTIMATING: 'bg-blue-50 text-[#002147] border-blue-200',
  REVIEW_REQUIRED: 'bg-amber-50 text-amber-700 border-amber-200',
  APPROVED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  DISPATCHED: 'bg-purple-50 text-purple-700 border-purple-200',
  Queued: 'bg-slate-50 text-[#64748b] border-slate-200',
  Processing: 'bg-blue-50 text-[#002147] border-blue-200',
  Complete: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Error: 'bg-red-50 text-red-700 border-red-200',
};

function isDone(status: string) {
  return ['APPROVED', 'DISPATCHED', 'Complete', 'REVIEW_REQUIRED'].includes(status);
}

function fmtAED(value: number | undefined | null): string {
  if (value === undefined || value === null) return 'TBD';
  return `AED ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtNum(value: number | undefined | null, decimals = 2): string {
  if (value === undefined || value === null) return 'TBD';
  return value.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

type TabKey = 'summary' | 'bom' | 'scope' | 'financial' | 'engineering' | 'compliance' | 'cutting' | 'drawings';

// Helper to normalize opening schedule data into an array
function normalizeOpenings(raw: Record<string, unknown> | OpeningItem[] | undefined | null): OpeningItem[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  for (const key of ['openings', 'items', 'schedule', 'opening_schedule']) {
    const val = raw[key];
    if (Array.isArray(val)) return val;
  }
  const entries = Object.entries(raw);
  if (entries.length > 0 && typeof entries[0][1] === 'object' && entries[0][1] !== null) {
    return entries.map(([k, v]) => ({ opening_id: k, ...(v as Record<string, unknown>) }));
  }
  return [];
}

// Progress Screen

function ProgressScreen({ progress, message }: { progress: number; message: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-[#f8fafc] p-20">
      <div className="w-full max-w-md space-y-6 bg-white p-8 rounded-md shadow-sm border border-[#e2e8f0]">
        <div className="flex justify-between items-end mb-2">
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-[#002147] uppercase tracking-wider">Processing</span>
            <h3 className="text-sm font-medium text-[#1e293b] mt-1 max-w-xs truncate">{message || 'Initializing...'}</h3>
          </div>
          <span className="text-lg font-mono font-bold text-[#002147]">{progress}%</span>
        </div>
        <div className="h-2 bg-slate-100 w-full rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#002147] to-[#1e3a5f] transition-all duration-700 rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex items-center gap-2 text-[#64748b]">
          <Loader2 size={14} className="animate-spin" />
          <p className="text-xs font-medium">Extracting geometry and specifications...</p>
        </div>
      </div>
    </div>
  );
}

// HITL Banner

function HITLBanner({ triageId }: { triageId: string }) {
  return (
    <div className="mx-4 mt-4 p-4 bg-amber-50 border border-amber-200 rounded-md flex items-center justify-between">
      <div className="flex items-center gap-3">
        <AlertTriangle size={16} className="text-amber-600" />
        <div>
          <p className="text-sm font-semibold text-amber-800">Human Review Required</p>
          <p className="text-xs text-amber-600">AI confidence below threshold -- triage item #{triageId.slice(0, 8)}</p>
        </div>
      </div>
      <Link
        href="/triage"
        className="px-4 py-2 bg-[#d97706] hover:bg-[#b45309] text-white rounded-md text-xs font-semibold transition-all"
      >
        Review Now
      </Link>
    </div>
  );
}

// BOM Table with category grouping

function BOMTable({ items }: { items: BOMItem[] }) {
  if (!items || items.length === 0) {
    return <div className="text-center text-[#64748b] py-16 text-sm">No BOM items generated yet.</div>;
  }

  // Group by category
  const grouped = useMemo(() => {
    const map: Record<string, BOMItem[]> = {};
    items.forEach((item) => {
      const cat = (item.category || 'Uncategorised').toUpperCase();
      if (!map[cat]) map[cat] = [];
      map[cat].push(item);
    });
    return Object.entries(map);
  }, [items]);

  const totalAED = items.reduce((sum, item) => sum + (item.subtotal_aed || 0), 0);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#002147]">
            <th className="text-left py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider w-12">#</th>
            <th className="text-left py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Item Code</th>
            <th className="text-left py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Description</th>
            <th className="text-right py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Qty</th>
            <th className="text-right py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Unit</th>
            <th className="text-right py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Rate (AED)</th>
            <th className="text-right py-3 px-4 font-semibold text-white text-xs uppercase tracking-wider">Total (AED)</th>
          </tr>
        </thead>
        <tbody>
          {grouped.map(([category, catItems]) => {
            const catTotal = catItems.reduce((s, i) => s + (i.subtotal_aed || 0), 0);
            return (
              <React.Fragment key={category}>
                {/* Category header row */}
                <tr className="bg-slate-100 border-y border-[#e2e8f0]">
                  <td colSpan={7} className="py-2.5 px-4">
                    <span className="text-xs font-bold text-[#002147] uppercase tracking-wide">{category}</span>
                    <span className="text-xs text-[#64748b] ml-3 font-mono">{catItems.length} items</span>
                  </td>
                </tr>
                {/* Items */}
                {catItems.map((item, i) => (
                  <tr key={`${category}-${i}`} className={`border-b border-[#e2e8f0] ${i % 2 === 1 ? 'bg-slate-50/50' : ''}`}>
                    <td className="py-2.5 px-4 text-[#64748b] text-xs">{i + 1}</td>
                    <td className="py-2.5 px-4 text-[#1e293b] font-mono text-xs">{item.item_code || '--'}</td>
                    <td className="py-2.5 px-4 text-[#1e293b]">{item.description || '--'}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{fmtNum(item.quantity)}</td>
                    <td className="py-2.5 px-4 text-right text-[#64748b] text-xs">{item.unit || '--'}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{item.unit_rate?.toFixed(2) || 'TBD'}</td>
                    <td className="py-2.5 px-4 text-right font-mono font-semibold text-[#1e293b]">
                      {item.subtotal_aed?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || 'TBD'}
                    </td>
                  </tr>
                ))}
                {/* Category subtotal */}
                <tr className="bg-[#002147]/5 border-b border-[#e2e8f0]">
                  <td colSpan={6} className="py-2.5 px-4 text-right text-xs font-semibold text-[#002147]">
                    {category} Subtotal
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono font-bold text-[#002147] text-xs">
                    {fmtAED(catTotal)}
                  </td>
                </tr>
              </React.Fragment>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="bg-[#002147]">
            <td colSpan={6} className="py-3 px-4 text-right font-semibold text-white text-sm uppercase tracking-wider">
              Grand Total
            </td>
            <td className="py-3 px-4 text-right font-mono font-bold text-white text-sm">
              {fmtAED(totalAED)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

// Openings Summary Section

function OpeningsSummary({ openings }: { openings: OpeningItem[] }) {
  if (!openings || openings.length === 0) return null;

  const totalArea = openings.reduce((sum, o) => {
    const w = o.width ?? o.width_mm ?? 0;
    const h = o.height ?? o.height_mm ?? 0;
    const a = o.area ?? o.area_sqm ?? (w > 0 && h > 0 ? (w * h) / 1_000_000 : 0);
    return sum + a;
  }, 0);

  const totalQty = openings.reduce((sum, o) => sum + (o.quantity ?? o.qty ?? 1), 0);

  const byType: Record<string, number> = {};
  openings.forEach((o) => {
    const t = o.type || o.opening_type || 'Unknown';
    byType[t] = (byType[t] || 0) + (o.quantity ?? o.qty ?? 1);
  });

  return (
    <div className="bg-gradient-to-r from-[#002147] to-[#1e3a5f] rounded-md p-6 text-white">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-[#94a3b8] mb-4">Openings Summary</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div>
          <div className="text-[10px] text-white/60 font-medium">Total Facade Area</div>
          <div className="text-xl font-bold font-mono">{fmtNum(totalArea, 1)} sqm</div>
        </div>
        <div>
          <div className="text-[10px] text-white/60 font-medium">Total Openings</div>
          <div className="text-xl font-bold font-mono">{totalQty}</div>
        </div>
        {Object.entries(byType).slice(0, 2).map(([type, count]) => (
          <div key={type}>
            <div className="text-[10px] text-white/60 font-medium">{type}</div>
            <div className="text-xl font-bold font-mono">{count}</div>
          </div>
        ))}
      </div>
      {Object.entries(byType).length > 2 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(byType).slice(2).map(([type, count]) => (
            <span key={type} className="text-xs bg-white/10 rounded-md px-2 py-1">
              {type}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// Opening Schedule Table

function OpeningScheduleTable({ openings }: { openings: OpeningItem[] }) {
  if (!openings || openings.length === 0) return null;

  const totalArea = openings.reduce((sum, o) => {
    const w = o.width ?? o.width_mm ?? 0;
    const h = o.height ?? o.height_mm ?? 0;
    return sum + (o.area ?? o.area_sqm ?? (w > 0 && h > 0 ? (w * h) / 1_000_000 : 0));
  }, 0);

  const totalGlassArea = openings.reduce((sum, o) => sum + (o.glass_area ?? o.glass_area_sqm ?? 0), 0);
  const totalQty = openings.reduce((sum, o) => sum + (o.quantity ?? o.qty ?? 1), 0);
  const totalAluWeight = openings.reduce((sum, o) => sum + (Number(o.alu_weight_kg ?? o.aluminum_weight_kg ?? 0)), 0);

  return (
    <div className="bg-white rounded-md border border-[#e2e8f0] overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[#002147]">
            <th className="text-left py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">Mark ID</th>
            <th className="text-left py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">System Type</th>
            <th className="text-right py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">W (mm)</th>
            <th className="text-right py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">H (mm)</th>
            <th className="text-right py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">Qty</th>
            <th className="text-right py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">Area (sqm)</th>
            <th className="text-left py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">Glass Spec</th>
            <th className="text-right py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">ALU Wt (kg)</th>
            <th className="text-left py-2.5 px-3 font-semibold text-white text-xs uppercase tracking-wider">Floor</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#e2e8f0]">
          {openings.map((o, i) => {
            const w = o.width ?? o.width_mm ?? 0;
            const h = o.height ?? o.height_mm ?? 0;
            const a = o.area ?? o.area_sqm ?? (w > 0 && h > 0 ? (w * h) / 1_000_000 : 0);
            const q = o.quantity ?? o.qty ?? 1;
            const aluWt = Number(o.alu_weight_kg ?? o.aluminum_weight_kg ?? 0);
            const glassSpec = String(o.glass_spec ?? o.glass_makeup ?? o.glass_type ?? '');
            return (
              <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                <td className="py-2 px-3 text-[#1e293b] font-mono text-xs">{o.mark_id || o.opening_id || o.id || `O-${String(i + 1).padStart(2, '0')}`}</td>
                <td className="py-2 px-3 text-xs">
                  {(o.system_type || o.system) ? (
                    <span className="inline-block px-2 py-0.5 bg-blue-50 text-[#002147] rounded-md text-xs border border-blue-200">
                      {o.system_type || o.system}
                    </span>
                  ) : (o.type || o.opening_type || '--')}
                </td>
                <td className="py-2 px-3 text-right font-mono text-[#1e293b] text-xs">{w > 0 ? fmtNum(w, 0) : '--'}</td>
                <td className="py-2 px-3 text-right font-mono text-[#1e293b] text-xs">{h > 0 ? fmtNum(h, 0) : '--'}</td>
                <td className="py-2 px-3 text-right font-mono text-[#1e293b] text-xs">{q}</td>
                <td className="py-2 px-3 text-right font-mono text-[#1e293b] text-xs">{a > 0 ? fmtNum(a, 2) : '--'}</td>
                <td className="py-2 px-3 text-xs text-[#1e293b]">
                  {glassSpec ? (
                    <span className="inline-block px-1.5 py-0.5 bg-cyan-50 text-cyan-800 rounded text-[10px] border border-cyan-200 max-w-[140px] truncate" title={glassSpec}>
                      {glassSpec}
                    </span>
                  ) : '--'}
                </td>
                <td className="py-2 px-3 text-right font-mono text-[#1e293b] text-xs">{aluWt > 0 ? fmtNum(aluWt, 1) : '--'}</td>
                <td className="py-2 px-3 text-[#64748b] text-xs">{o.floor ?? '--'}</td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="bg-slate-100 border-t-2 border-[#e2e8f0]">
            <td colSpan={4} className="py-2.5 px-3 text-xs font-semibold text-[#002147]">
              Total: {openings.length} openings
            </td>
            <td className="py-2.5 px-3 text-right font-mono font-bold text-[#002147] text-xs">
              {totalQty}
            </td>
            <td className="py-2.5 px-3 text-right font-mono font-bold text-[#002147] text-xs">
              {fmtNum(totalArea, 2)}
            </td>
            <td className="py-2.5 px-3"></td>
            <td className="py-2.5 px-3 text-right font-mono font-bold text-[#002147] text-xs">
              {totalAluWeight > 0 ? fmtNum(totalAluWeight, 1) : '--'}
            </td>
            <td className="py-2.5 px-3"></td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

// Scope Tab with opening schedule table

function ScopeTab({ scope, openings }: { scope: Record<string, unknown>; openings: Record<string, unknown> | OpeningItem[] }) {
  const scopeEntries = Object.entries(scope || {});
  const openingsList = normalizeOpenings(openings);

  if (scopeEntries.length === 0 && openingsList.length === 0) {
    return <div className="text-center text-[#64748b] py-16 text-sm">No scope data available.</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Project Scope key-value pairs */}
      {scopeEntries.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-3">Project Scope</h3>
          <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-[#e2e8f0]">
                {scopeEntries.map(([key, value]) => (
                  <tr key={key} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-4 text-xs font-medium text-[#64748b] w-1/3 capitalize">
                      {key.replace(/_/g, ' ')}
                    </td>
                    <td className="py-2.5 px-4 text-xs text-[#1e293b] font-mono">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value ?? '--')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Floor & Elevation Breakdown */}
      {openingsList.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* By System Type */}
          {(() => {
            const byType: Record<string, { count: number; area: number }> = {};
            openingsList.forEach((op) => {
              const t = String(op.system_type || op.type || op.opening_type || 'Unknown');
              if (!byType[t]) byType[t] = { count: 0, area: 0 };
              const qty = Number(op.quantity || op.qty || 1);
              const w = Number(op.width_mm || op.width || 0);
              const h = Number(op.height_mm || op.height || 0);
              byType[t].count += qty;
              byType[t].area += (w / 1000) * (h / 1000) * qty;
            });
            const sorted = Object.entries(byType).sort((a, b) => b[1].count - a[1].count);
            return (
              <div className="bg-white rounded-md border border-slate-200 p-4">
                <h4 className="text-xs font-semibold text-[#002147] mb-2">By System Type</h4>
                <div className="space-y-1.5">
                  {sorted.map(([type, { count, area }]) => (
                    <div key={type} className="flex justify-between text-xs">
                      <span className="text-slate-600 truncate mr-2">{type}</span>
                      <span className="font-mono text-slate-800 whitespace-nowrap">{count} pcs / {area.toFixed(1)} sqm</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* By Floor */}
          {(() => {
            const byFloor: Record<string, number> = {};
            openingsList.forEach((op) => {
              const f = String(op.floor || 'Unknown');
              const qty = Number(op.quantity || op.qty || 1);
              byFloor[f] = (byFloor[f] || 0) + qty;
            });
            return (
              <div className="bg-white rounded-md border border-slate-200 p-4">
                <h4 className="text-xs font-semibold text-[#002147] mb-2">By Floor</h4>
                <div className="space-y-1.5">
                  {Object.entries(byFloor).map(([floor, count]) => (
                    <div key={floor} className="flex justify-between text-xs">
                      <span className="text-slate-600">{floor}</span>
                      <span className="font-mono text-slate-800">{count} items</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* By Elevation */}
          {(() => {
            const byElev: Record<string, number> = {};
            openingsList.forEach((op) => {
              const e = String((op as Record<string, unknown>).elevation || 'Unknown');
              const qty = Number(op.quantity || op.qty || 1);
              byElev[e] = (byElev[e] || 0) + qty;
            });
            return (
              <div className="bg-white rounded-md border border-slate-200 p-4">
                <h4 className="text-xs font-semibold text-[#002147] mb-2">By Elevation</h4>
                <div className="space-y-1.5">
                  {Object.entries(byElev).map(([elev, count]) => (
                    <div key={elev} className="flex justify-between text-xs">
                      <span className="text-slate-600">{elev}</span>
                      <span className="font-mono text-slate-800">{count} items</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* Opening Schedule Table */}
      {openingsList.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-3">
            Opening Schedule ({openingsList.length} items)
          </h3>
          <OpeningScheduleTable openings={openingsList} />
        </div>
      )}
    </div>
  );
}

// Engineering Tab

function EngineeringTab({
  openings,
  structural,
  engineeringResults,
  id,
}: {
  openings: OpeningItem[];
  structural: EstimateDetail['structural_results'];
  engineeringResults: EstimateDetail['engineering_results'];
  id: string;
}) {
  const summary = engineeringResults?.summary;
  const windLoadAnalysis = engineeringResults?.wind_load_analysis;
  const thermalAnalysis = engineeringResults?.thermal_analysis;
  const deflectionChecks = engineeringResults?.deflection_checks;
  const glassStressChecks = engineeringResults?.glass_stress_checks;

  const hasEngineeringData = summary || windLoadAnalysis?.length || thermalAnalysis?.length || deflectionChecks?.length || glassStressChecks?.length;

  const statusBadge = (status: string) => {
    const s = status?.toUpperCase();
    if (s === 'PASS' || s === 'OK') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (s === 'FAIL') return 'bg-red-50 text-red-700 border-red-200';
    if (s === 'WARNING' || s === 'WARN') return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-slate-50 text-slate-600 border-slate-200';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Engineering Summary */}
      {summary && (
        <div className="bg-gradient-to-r from-[#002147] to-[#1e3a5f] rounded-md p-6 text-white">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-[#94a3b8] mb-4">Engineering Analysis Summary</h3>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div>
              <div className="text-[10px] text-white/60 font-medium">Total Checks</div>
              <div className="text-xl font-bold font-mono">{summary.total_checks}</div>
            </div>
            <div>
              <div className="text-[10px] text-white/60 font-medium">Pass</div>
              <div className="text-xl font-bold font-mono text-emerald-300">{summary.pass}</div>
            </div>
            <div>
              <div className="text-[10px] text-white/60 font-medium">Fail</div>
              <div className="text-xl font-bold font-mono text-red-300">{summary.fail}</div>
            </div>
            <div>
              <div className="text-[10px] text-white/60 font-medium">Warning</div>
              <div className="text-xl font-bold font-mono text-amber-300">{summary.warning}</div>
            </div>
            <div>
              <div className="text-[10px] text-white/60 font-medium">Compliance</div>
              <div className="text-xl font-bold font-mono">{summary.compliance_pct?.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}

      {/* Opening Schedule */}
      {openings.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-3">Opening Schedule</h3>
          <OpeningScheduleTable openings={openings} />
        </div>
      )}

      {/* Wind Load Analysis (engineering_results version) */}
      {windLoadAnalysis && windLoadAnalysis.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-3">Wind Load Analysis</h3>
          <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#002147]">
                  <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Opening</th>
                  <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Check</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Wind Pressure (Pa)</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Safety Factor</th>
                  <th className="text-center py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e2e8f0]">
                {windLoadAnalysis.map((w, i) => (
                  <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                    <td className="py-2.5 px-4 text-[#1e293b] font-mono text-xs">{w.opening_id}</td>
                    <td className="py-2.5 px-4 text-[#1e293b] text-xs">{w.check}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{w.wind_pressure_pa?.toFixed(1) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{w.safety_factor?.toFixed(2) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${statusBadge(w.status)}`}>
                        {w.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Thermal Analysis (engineering_results version) */}
      {thermalAnalysis && thermalAnalysis.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-3">Thermal Analysis</h3>
          <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#002147]">
                  <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Opening</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">U-Value (W/m2K)</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Target U-Value</th>
                  <th className="text-center py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e2e8f0]">
                {thermalAnalysis.map((t, i) => (
                  <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                    <td className="py-2.5 px-4 text-[#1e293b] font-mono text-xs">{t.opening_id}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{t.u_value_w_m2k?.toFixed(2) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{t.target_u_value?.toFixed(2) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${statusBadge(t.status)}`}>
                        {t.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Deflection Checks */}
      {deflectionChecks && deflectionChecks.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-3">Deflection Checks</h3>
          <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#002147]">
                  <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Opening</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Deflection (mm)</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Allowable (mm)</th>
                  <th className="text-center py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e2e8f0]">
                {deflectionChecks.map((d, i) => (
                  <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                    <td className="py-2.5 px-4 text-[#1e293b] font-mono text-xs">{d.opening_id}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{d.deflection_mm?.toFixed(2) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{d.allowable_mm?.toFixed(2) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${statusBadge(d.status)}`}>
                        {d.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Glass Stress Checks */}
      {glassStressChecks && glassStressChecks.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-3">Glass Stress Checks</h3>
          <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#002147]">
                  <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Opening</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Applied (MPa)</th>
                  <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Allowable (MPa)</th>
                  <th className="text-center py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e2e8f0]">
                {glassStressChecks.map((g, i) => (
                  <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                    <td className="py-2.5 px-4 text-[#1e293b] font-mono text-xs">{g.opening_id}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{g.applied_stress_mpa?.toFixed(2) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{g.allowable_stress_mpa?.toFixed(2) ?? '--'}</td>
                    <td className="py-2.5 px-4 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${statusBadge(g.status)}`}>
                        {g.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Fallback: legacy structural_results */}
      {!hasEngineeringData && structural && structural.length > 0 && (
        <>
          <div>
            <h3 className="text-sm font-semibold text-[#002147] mb-3">Wind Load Analysis</h3>
            <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[#002147]">
                    <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">System Type</th>
                    <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Wind Load (kPa)</th>
                    <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Deflection (mm)</th>
                    <th className="text-center py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#e2e8f0]">
                  {structural.map((s, i) => (
                    <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                      <td className="py-2.5 px-4 text-[#1e293b]">{s.system_type || `System ${i + 1}`}</td>
                      <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{s.wind_load_kpa?.toFixed(2) ?? '--'}</td>
                      <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{s.deflection_mm?.toFixed(2) ?? '--'}</td>
                      <td className="py-2.5 px-4 text-center">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${s.pass ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                          {s.pass ? 'PASS' : 'FAIL'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {structural.some(s => s.thermal_u_value !== undefined) && (
            <div>
              <h3 className="text-sm font-semibold text-[#002147] mb-3">Thermal Performance</h3>
              <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-[#002147]">
                      <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">System Type</th>
                      <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">U-Value (W/m2K)</th>
                      <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Acoustic Rw (dB)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#e2e8f0]">
                    {structural.filter(s => s.thermal_u_value !== undefined).map((s, i) => (
                      <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                        <td className="py-2.5 px-4 text-[#1e293b]">{s.system_type || `System ${i + 1}`}</td>
                        <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{s.thermal_u_value?.toFixed(2) ?? '--'}</td>
                        <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{s.acoustic_rw ?? '--'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {(!hasEngineeringData && (!structural || structural.length === 0)) && openings.length === 0 && (
        <div className="text-center text-[#64748b] py-16 text-sm">
          <p>No engineering data available yet.</p>
          <Link href={`/estimate/${id}/compliance`} className="text-[#002147] hover:underline text-xs mt-2 inline-block">
            View full compliance report
          </Link>
        </div>
      )}
    </div>
  );
}

// Financial Tab

function FinancialTab({ financial, boqSummary, bomSummary }: { financial: FinancialSummary; boqSummary?: EstimateDetail['boq']['summary']; bomSummary?: Record<string, unknown> }) {
  const rows: [string, string, string][] = [];

  if (financial.material_cost_aed !== undefined) rows.push(['Material Cost', fmtAED(financial.material_cost_aed), 'text-[#1e293b]']);
  if (financial.labor_cost_aed !== undefined) rows.push(['Labor Cost', fmtAED(financial.labor_cost_aed), 'text-[#1e293b]']);

  // Factory overhead
  const factoryOverhead = financial.factory_overhead_aed ?? 70000;
  rows.push(['Factory Overhead (monthly)', fmtAED(factoryOverhead), 'text-[#1e293b]']);

  if (financial.overhead_aed !== undefined) rows.push(['General Overhead', fmtAED(financial.overhead_aed), 'text-[#1e293b]']);

  // Separate lines for project management, design, insurance, warranty
  if (financial.project_management_aed !== undefined) rows.push(['Project Management', fmtAED(financial.project_management_aed), 'text-[#64748b]']);
  if (financial.design_fee_aed !== undefined) rows.push(['Design Fee', fmtAED(financial.design_fee_aed), 'text-[#64748b]']);
  if (financial.insurance_aed !== undefined) rows.push(['Insurance', fmtAED(financial.insurance_aed), 'text-[#64748b]']);
  if (financial.warranty_aed !== undefined) rows.push(['Warranty Provision', fmtAED(financial.warranty_aed), 'text-[#64748b]']);

  if (financial.attic_stock_cost_aed !== undefined) rows.push(['Attic Stock (2%)', fmtAED(financial.attic_stock_cost_aed), 'text-[#64748b]']);
  if (financial.provisional_sums_aed !== undefined) rows.push(['Provisional Sums', fmtAED(financial.provisional_sums_aed), 'text-[#64748b]']);
  if (financial.margin_aed !== undefined) rows.push(['Margin', fmtAED(financial.margin_aed), 'text-[#059669]']);
  if (financial.gross_margin_pct !== undefined) rows.push(['Gross Margin', `${(financial.gross_margin_pct * 100).toFixed(1)}%`, 'text-[#059669]']);

  if (boqSummary?.total_direct_cost_aed !== undefined) rows.push(['Total Direct Cost', fmtAED(boqSummary.total_direct_cost_aed), 'text-[#1e293b]']);
  if (boqSummary?.total_weight_kg !== undefined) rows.push(['Total Weight', `${fmtNum(boqSummary.total_weight_kg, 1)} kg`, 'text-[#64748b]']);

  const totalAED = financial.total_aed ?? boqSummary?.total_sell_price_aed;

  // VAT calculation
  const vatAmount = financial.vat_aed ?? (totalAED ? totalAED * 0.05 : undefined);
  const totalInclVat = financial.total_incl_vat_aed ?? (totalAED && vatAmount ? totalAED + vatAmount : undefined);

  if (rows.length === 0 && totalAED === undefined) {
    return <div className="text-center text-[#64748b] py-16 text-sm">No financial data available.</div>;
  }

  return (
    <div className="p-6">
      <div className="max-w-xl">
        <h3 className="text-sm font-semibold text-[#002147] mb-4">Financial Breakdown</h3>
        <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
          <div className="divide-y divide-[#e2e8f0]">
            {rows.map(([label, value, color]) => (
              <div key={label} className="flex justify-between py-3 px-4 text-sm">
                <span className="text-[#64748b]">{label}</span>
                <span className={`font-mono font-medium ${color}`}>{value}</span>
              </div>
            ))}
          </div>
          {totalAED !== undefined && (
            <>
              <div className="flex justify-between py-3 px-4 border-t-2 border-[#002147] bg-slate-50">
                <span className="font-semibold text-[#002147]">Subtotal (excl. VAT)</span>
                <span className="font-mono font-bold text-lg text-[#002147]">{fmtAED(totalAED)}</span>
              </div>
              {vatAmount !== undefined && (
                <div className="flex justify-between py-3 px-4 border-t border-[#e2e8f0]">
                  <span className="text-[#64748b]">VAT (5%)</span>
                  <span className="font-mono font-medium text-[#1e293b]">{fmtAED(vatAmount)}</span>
                </div>
              )}
              {totalInclVat !== undefined && (
                <div className="flex justify-between py-4 px-4 border-t-2 border-[#94a3b8] bg-[#002147]">
                  <span className="font-semibold text-white">Total (incl. VAT)</span>
                  <span className="font-mono font-bold text-lg text-[#94a3b8]">{fmtAED(totalInclVat)}</span>
                </div>
              )}
            </>
          )}
        </div>
        {financial.retention_pct !== undefined && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-700">
            Note: {financial.retention_pct}% retention locked for 12 months (not included in cashflow).
          </div>
        )}
      </div>
    </div>
  );
}

// Compliance Tab

function ComplianceTab({ structural, id }: { structural: EstimateDetail['structural_results']; id: string }) {
  if (!structural || structural.length === 0) {
    return (
      <div className="text-center text-[#64748b] py-16 text-sm">
        <p>No compliance data available.</p>
        <Link href={`/estimate/${id}/compliance`} className="text-[#002147] hover:underline text-xs mt-2 inline-block">
          View full compliance report
        </Link>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#002147]">Structural Check Summary</h3>
        <Link href={`/estimate/${id}/compliance`} className="text-xs text-[#002147] hover:underline flex items-center gap-1">
          Full Report <ChevronRight size={12} />
        </Link>
      </div>
      <div className="bg-white rounded-md border border-[#e2e8f0] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#002147]">
              <th className="text-left py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">System Type</th>
              <th className="text-right py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Deflection (mm)</th>
              <th className="text-center py-2.5 px-4 font-semibold text-white text-xs uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#e2e8f0]">
            {structural.map((s, i) => (
              <tr key={i} className={i % 2 === 1 ? 'bg-slate-50/50' : ''}>
                <td className="py-2.5 px-4 text-[#1e293b]">{s.system_type || `System ${i + 1}`}</td>
                <td className="py-2.5 px-4 text-right font-mono text-[#1e293b]">{s.deflection_mm?.toFixed(2) ?? '--'}</td>
                <td className="py-2.5 px-4 text-center">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${s.pass ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                    {s.pass ? 'PASS' : 'FAIL'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Drawings Tab

function DrawingsTab({ estimateId }: { estimateId: string }) {
  const [drawings, setDrawings] = React.useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [generating, setGenerating] = React.useState<string | null>(null);

  React.useEffect(() => {
    const fetchDrawings = async () => {
      setLoading(true);
      try {
        const data = await apiGet<Record<string, unknown>>(`/api/reports/estimate/${estimateId}/drawings`);
        setDrawings(data);
      } catch {
        // Non-fatal: drawings endpoint may not be available yet
      }
      setLoading(false);
    };
    fetchDrawings();
  }, [estimateId]);

  const handleDownload = async (drawingType: string) => {
    setGenerating(drawingType);
    try {
      const response = await apiFetch(`/api/reports/estimate/${estimateId}/drawing/${drawingType}`);
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${drawingType}_${estimateId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Failed: ${e}`);
    }
    setGenerating(null);
  };

  const DRAWING_TYPES = [
    { key: 'elevation', name: 'Elevation Markup', desc: 'Facade elevation with all openings tagged by Mark ID', Icon: Ruler },
    { key: 'shop_drawing', name: 'Shop Drawings', desc: 'Cross-section details for each system type (Curtain Wall, Shopfront, etc.)', Icon: Layers },
    { key: 'acp_layout', name: 'ACP Panel Layouts', desc: 'Flat-sheet routing & folding dimensions for ACP panels', Icon: Grid3X3 },
  ];

  if (loading) {
    return (
      <div className="p-6 flex justify-center">
        <Loader2 size={24} className="animate-spin text-slate-300" />
      </div>
    );
  }

  const drawingsData = drawings as Record<string, unknown> | null;
  const drawingsList = (drawingsData?.drawings ?? []) as unknown[];

  return (
    <div className="p-6">
      <h3 className="text-sm font-semibold text-[#002147] mb-4">Drawings &amp; Shop Details</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {DRAWING_TYPES.map(dt => (
          <div key={dt.key} className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col justify-between">
            <div>
              <div className="mb-2 text-[#002147]">
                <dt.Icon size={28} />
              </div>
              <h4 className="text-sm font-semibold text-[#002147] mb-1">{dt.name}</h4>
              <p className="text-xs text-slate-500 mb-4">{dt.desc}</p>
            </div>
            <button
              onClick={() => handleDownload(dt.key)}
              disabled={generating === dt.key}
              className="w-full px-4 py-2 bg-[#002147] hover:bg-[#1e3a5f] text-white rounded-md text-xs font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {generating === dt.key ? (
                <><Loader2 size={14} className="animate-spin" /> Generating...</>
              ) : (
                <><Download size={14} /> Download PDF</>
              )}
            </button>
          </div>
        ))}
      </div>
      {drawingsList.length > 0 && (
        <div className="mt-4 text-xs text-slate-400">
          {String((drawingsData as Record<string, unknown>)?.drawing_count ?? drawingsList.length)} drawings generated
          {(drawingsData as Record<string, unknown>)?.generated_at
            ? ` at ${new Date(String((drawingsData as Record<string, unknown>).generated_at)).toLocaleString()}`
            : ''}
        </div>
      )}
    </div>
  );
}

// Cutting List Tab
function CuttingListTab({ cuttingList }: { cuttingList: Record<string, unknown> }) {
  const sections = (cuttingList?.sections || cuttingList) as Record<string, unknown>;
  const alProfiles = (sections?.aluminum_profiles || {}) as Record<string, unknown>;
  const profiles = (alProfiles?.profiles || []) as Array<Record<string, unknown>>;
  const avgYield = Number(alProfiles?.average_yield_pct || 0);
  const totalBars = profiles.reduce((sum, p) => sum + Number(p.bars_required || 0), 0);
  const totalLength = profiles.reduce((sum, p) => sum + Number(p.total_cut_length_mm || 0), 0);

  const glassSchedule = (sections?.glass_cutting || sections?.glass_schedule || {}) as Record<string, unknown>;
  const glassItems = (glassSchedule?.items || glassSchedule?.panels || []) as Array<Record<string, unknown>>;

  const hasData = profiles.length > 0 || glassItems.length > 0;

  if (!hasData) {
    return (
      <div className="text-center py-16 text-slate-400">
        <Scissors size={32} className="mx-auto mb-3 opacity-40" />
        <p className="font-medium">No cutting list data available</p>
        <p className="text-xs mt-1">Cutting list is generated during the estimation pipeline</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Profiles', value: profiles.length, unit: 'types' },
          { label: 'Bars Required', value: totalBars, unit: 'pcs' },
          { label: 'Total Cut Length', value: `${(totalLength / 1000).toFixed(1)}`, unit: 'm' },
          { label: 'Avg Yield', value: `${avgYield.toFixed(1)}`, unit: '%' },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-slate-50 border border-slate-200 rounded-md p-3">
            <div className="text-xs text-slate-500">{kpi.label}</div>
            <div className="text-lg font-bold text-[#002147]">{kpi.value} <span className="text-xs text-slate-400 font-normal">{kpi.unit}</span></div>
          </div>
        ))}
      </div>

      {/* Aluminum Profiles Table */}
      {profiles.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-2 flex items-center gap-2">
            <Scissors size={14} /> Aluminum Cutting Schedule
          </h3>
          <div className="overflow-x-auto border border-slate-200 rounded-md">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-600">Profile</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Stock (mm)</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Cut Length (mm)</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Qty</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Bars</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Yield %</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Waste (mm)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {profiles.map((p, i) => {
                  const yieldPct = Number(p.yield_pct || p.utilization_pct || 0);
                  return (
                    <tr key={i} className="hover:bg-slate-50/50">
                      <td className="py-2 px-3 font-mono text-xs">{String(p.profile_name || p.profile_ref || p.name || `P${i + 1}`)}</td>
                      <td className="py-2 px-3 text-right font-mono">{Number(p.stock_length_mm || 6500)}</td>
                      <td className="py-2 px-3 text-right font-mono">{Number(p.cut_length_mm || p.length_mm || 0)}</td>
                      <td className="py-2 px-3 text-right font-mono">{Number(p.quantity || p.qty || 0)}</td>
                      <td className="py-2 px-3 text-right font-mono font-medium">{Number(p.bars_required || 0)}</td>
                      <td className={`py-2 px-3 text-right font-mono font-medium ${yieldPct >= 85 ? 'text-green-600' : yieldPct >= 70 ? 'text-amber-600' : 'text-red-600'}`}>
                        {yieldPct.toFixed(1)}
                      </td>
                      <td className="py-2 px-3 text-right font-mono text-slate-400">{Number(p.waste_mm || p.offcut_mm || 0)}</td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="bg-slate-50 border-t border-slate-300 font-semibold text-xs">
                  <td className="py-2 px-3 text-[#002147]">TOTALS</td>
                  <td className="py-2 px-3"></td>
                  <td className="py-2 px-3 text-right font-mono">{(totalLength).toFixed(0)}</td>
                  <td className="py-2 px-3"></td>
                  <td className="py-2 px-3 text-right font-mono">{totalBars}</td>
                  <td className="py-2 px-3 text-right font-mono">{avgYield.toFixed(1)}</td>
                  <td className="py-2 px-3"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Glass Schedule */}
      {glassItems.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[#002147] mb-2">Glass Cutting Schedule</h3>
          <div className="overflow-x-auto border border-slate-200 rounded-md">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-600">Mark</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">W (mm)</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">H (mm)</th>
                  <th className="text-left py-2 px-3 text-xs font-semibold text-slate-600">Glass Type</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Qty</th>
                  <th className="text-right py-2 px-3 text-xs font-semibold text-slate-600">Area (sqm)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {glassItems.map((g, i) => (
                  <tr key={i} className="hover:bg-slate-50/50">
                    <td className="py-2 px-3 font-mono text-xs">{String(g.mark_id || g.opening_id || `G${i + 1}`)}</td>
                    <td className="py-2 px-3 text-right font-mono">{Number(g.width_mm || g.width || 0)}</td>
                    <td className="py-2 px-3 text-right font-mono">{Number(g.height_mm || g.height || 0)}</td>
                    <td className="py-2 px-3 text-xs">{String(g.glass_type || g.glass_spec || '--')}</td>
                    <td className="py-2 px-3 text-right font-mono">{Number(g.quantity || g.qty || 1)}</td>
                    <td className="py-2 px-3 text-right font-mono">{Number(g.area_sqm || 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// Main Component

const EstimatePage = () => {
  const router = useRouter();
  const { id } = router.query;
  const [mounted, setMounted] = useState(false);
  const [progress, setProgress] = useState<SSEProgress | null>(null);
  const [estimate, setEstimate] = useState<EstimateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('summary');
  const [downloading, setDownloading] = useState(false);
  const sseRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { setMounted(true); }, []);

  const fetchEstimate = async (estimateId: string) => {
    try {
      const data = await apiGet<EstimateDetail>(`/api/ingestion/estimate/${estimateId}`);
      setEstimate(data);
      return data;
    } catch (e) {
      setError(String(e));
      return null;
    }
  };

  // SSE + polling
  useEffect(() => {
    if (!mounted || !id) return;
    const estimateId = id as string;

    const startSSE = () => {
      const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/ingestion/progress/${estimateId}`;
      const es = new EventSource(url);
      sseRef.current = es;

      es.onmessage = (event) => {
        try {
          const payload: SSEProgress = JSON.parse(event.data);
          setProgress(payload);
          if (isDone(payload.partial_results?.status || '')) {
            es.close();
            fetchEstimate(estimateId);
          }
        } catch { /* ignore parse errors */ }
      };

      es.onerror = () => {
        es.close();
        startPolling(estimateId);
      };
    };

    const startPolling = (eid: string) => {
      if (pollRef.current) return;
      pollRef.current = setInterval(async () => {
        try {
          const status = await apiGet<{
            estimate_id: string;
            status: string;
            progress_pct: number;
            current_step: string;
          }>(`/api/ingestion/status/${eid}`);

          setProgress(prev => ({
            ...(prev || { estimate_id: eid, current_agent: '', confidence_score: 1, partial_results: {} }),
            status_message: status.current_step || status.status,
            progress_pct: status.progress_pct || 0,
            partial_results: { status: status.status },
          }));

          if (isDone(status.status)) {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            fetchEstimate(eid);
          }
        } catch { /* ignore */ }
      }, 3000);
    };

    fetchEstimate(estimateId).then((data) => {
      if (data && isDone(data.status)) return;
      startSSE();
    });

    return () => {
      sseRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [mounted, id]);

  const handleDownloadPDF = async () => {
    if (!id) return;
    setDownloading(true);
    try {
      const response = await apiFetch(`/api/reports/estimate/${id}/pdf`, { method: 'GET' });
      if (!response.ok) throw new Error('PDF generation failed');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `estimate-${(id as string).slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Failed to download PDF: ${e}`);
    } finally {
      setDownloading(false);
    }
  };

  const handlePrint = () => { window.print(); };

  if (!mounted) return <div className="min-h-screen bg-[#f8fafc]" />;

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertTriangle size={40} className="mx-auto text-red-400" />
          <p className="text-[#1e293b] font-semibold">Failed to load estimate</p>
          <p className="text-xs text-red-500 max-w-md">{error}</p>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 bg-[#002147] hover:bg-[#1e3a5f] text-white rounded-md text-sm font-medium transition-all"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const currentStatus = estimate?.status || progress?.partial_results?.status || '';
  const showProgress = !estimate || !isDone(currentStatus);

  if (showProgress) {
    const pct = progress?.progress_pct ?? estimate?.progress_pct ?? 0;
    const msg = progress?.status_message ?? estimate?.current_step ?? 'Initializing...';

    if (progress?.hitl_required && progress.hitl_triage_id) {
      return (
        <div className="flex-1 flex flex-col">
          <HITLBanner triageId={progress.hitl_triage_id} />
          <ProgressScreen progress={pct} message={msg} />
        </div>
      );
    }

    return <ProgressScreen progress={pct} message={msg} />;
  }

  // Data extraction

  const bomItems: BOMItem[] = estimate.bom_output?.items ?? [];
  const boqItems = estimate.boq?.line_items ?? [];
  const boqSummary = estimate.boq?.summary;
  const financialRates = estimate.boq?.financial_rates;
  const financial = estimate.financial_summary || {};
  const rfiCount = estimate.rfi_register?.length ?? 0;
  const veTotal = estimate.ve_opportunities?.reduce((s, v) => s + (v.saving_aed || 0), 0) ?? 0;
  const openingsList = normalizeOpenings(estimate.opening_schedule);
  const engineeringResults = estimate.engineering_results ||
    (estimate.state_snapshot?.engineering_results as EstimateDetail['engineering_results']) || undefined;

  // Use BOM items if available, fall back to BOQ line items
  const displayBomItems: BOMItem[] = bomItems.length > 0
    ? bomItems
    : boqItems.map(item => ({
        item_code: item.item_code,
        description: item.description,
        category: item.system_type,
        quantity: item.quantity,
        unit: item.unit,
        unit_rate: item.unit_rate_aed,
        subtotal_aed: item.total_aed,
      }));

  const totalContractValue = financial.total_aed ?? boqSummary?.total_sell_price_aed;

  const TABS: { key: TabKey; label: string; icon: React.ElementType; count?: number }[] = [
    { key: 'summary', label: 'Summary', icon: ClipboardList },
    { key: 'bom', label: 'BOM', icon: Package, count: displayBomItems.length },
    { key: 'scope', label: 'Scope', icon: ListChecks, count: openingsList.length > 0 ? openingsList.length : undefined },
    { key: 'financial', label: 'Financial', icon: BarChart3 },
    { key: 'engineering', label: 'Engineering', icon: Wrench },
    { key: 'compliance', label: 'Compliance', icon: ShieldCheck },
    { key: 'cutting', label: 'Cutting List', icon: Scissors },
    { key: 'drawings', label: 'Drawings', icon: Ruler },
  ];

  return (
    <div className="flex flex-col gap-0 print:gap-0">

      {/* PROJECT HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 print:mb-4">
        <div className="flex items-start gap-4">
          <button onClick={() => router.push('/')} className="mt-1 p-1.5 hover:bg-slate-100 rounded-md transition-colors print:hidden">
            <ArrowLeft size={18} className="text-[#64748b]" />
          </button>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-xl font-bold text-[#002147]">
                {estimate.project_name || `Estimate #${(estimate.estimate_id || '').slice(0, 8)}`}
              </h1>
              <span className={`px-2.5 py-0.5 text-[11px] font-semibold rounded-md border ${STATUS_STYLES[currentStatus] || STATUS_STYLES['Queued']}`}>
                {currentStatus.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-[#64748b]">
              {estimate.client_name && (
                <>
                  <span className="flex items-center gap-1"><Briefcase size={12} /> {estimate.client_name}</span>
                  <span className="w-1 h-1 bg-[#e2e8f0] rounded-full" />
                </>
              )}
              <span className="flex items-center gap-1"><MapPin size={12} /> {estimate.location || 'UAE'}</span>
              <span className="w-1 h-1 bg-[#e2e8f0] rounded-full" />
              <span className="flex items-center gap-1"><Clock size={12} /> ID: {(estimate.estimate_id || '').slice(0, 12)}</span>
              {financialRates?.lme_aluminum_usd_mt && (
                <>
                  <span className="w-1 h-1 bg-[#e2e8f0] rounded-full" />
                  <span className="font-mono text-[#1e293b]">LME: ${financialRates.lme_aluminum_usd_mt.toFixed(0)}/MT</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 print:hidden">
          <button
            onClick={handleDownloadPDF}
            disabled={downloading}
            className="px-4 py-2 bg-[#002147] hover:bg-[#1e3a5f] text-white rounded-md text-xs font-medium transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download PDF
          </button>
          <button
            onClick={handlePrint}
            className="px-4 py-2 border border-[#e2e8f0] hover:bg-slate-50 text-[#1e293b] rounded-md text-xs font-medium transition-colors flex items-center gap-2"
          >
            <Printer size={14} /> Print
          </button>
          {currentStatus === 'REVIEW_REQUIRED' && (
            <Link
              href={`/estimate/${id}/approve`}
              className="px-4 py-2 bg-[#002147] hover:bg-[#1e3a5f] text-white rounded-md text-xs font-semibold transition-all flex items-center gap-2"
            >
              <ShieldAlert size={14} /> Approve
            </Link>
          )}
        </div>
      </div>

      {/* METRICS ROW */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6 print:grid-cols-4">
        {[
          {
            label: 'Contract Value',
            value: totalContractValue ? fmtAED(totalContractValue) : '--',
            icon: DollarSign,
            borderColor: 'border-l-[#3b82f6]',
          },
          {
            label: 'Gross Margin',
            value: (financial.gross_margin_pct ?? boqSummary?.gross_margin_pct)
              ? `${((financial.gross_margin_pct ?? boqSummary?.gross_margin_pct ?? 0) * 100).toFixed(1)}%`
              : '--',
            icon: TrendingUp,
            borderColor: 'border-l-[#059669]',
          },
          {
            label: 'BOM Items',
            value: String(displayBomItems.length),
            icon: Layers,
            borderColor: 'border-l-[#002147]',
          },
          {
            label: 'Open RFIs',
            value: String(rfiCount),
            icon: FileText,
            borderColor: 'border-l-[#d97706]',
          },
        ].map((m) => (
          <div key={m.label} className={`bg-white rounded-md border border-[#e2e8f0] border-l-4 ${m.borderColor} p-4 flex items-center gap-3 shadow-sm`}>
            <m.icon size={18} className="text-[#64748b]" />
            <div>
              <div className="text-[11px] text-[#64748b]">{m.label}</div>
              <div className="text-base font-semibold text-[#1e293b] font-mono">{m.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* TABS */}
      <div className="bg-white rounded-md border border-[#e2e8f0] flex-1 print:border-0 print:shadow-none shadow-sm">
        {/* Tab bar */}
        <div className="flex border-b border-[#e2e8f0] px-4 overflow-x-auto print:hidden">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'border-[#94a3b8] text-[#002147]'
                  : 'border-transparent text-[#64748b] hover:text-[#1e293b] hover:border-[#e2e8f0]'
              }`}
            >
              <tab.icon size={15} />
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="text-[11px] bg-slate-100 text-[#1e293b] px-1.5 py-0.5 rounded-md font-mono">{tab.count}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="min-h-[400px]">
          {/* SUMMARY TAB */}
          {activeTab === 'summary' && (
            <div className="p-6 space-y-6">
              {/* Openings Summary banner */}
              <OpeningsSummary openings={openingsList} />

              {/* Quick links */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Compliance Report', href: `/estimate/${id}/compliance`, icon: CheckCircle2 },
                  { label: 'RFI Log', href: `/estimate/${id}/rfi`, icon: FileText, badge: rfiCount > 0 ? rfiCount : undefined },
                  { label: 'VE Menu', href: `/estimate/${id}/ve-menu`, icon: TrendingUp, badge: veTotal > 0 ? `AED ${(veTotal / 1000).toFixed(0)}k` : undefined },
                  { label: 'Approval', href: `/estimate/${id}/approve`, icon: ShieldAlert },
                ].map((a) => (
                  <Link
                    key={a.href}
                    href={a.href}
                    className="flex items-center gap-3 p-3 rounded-md border border-[#e2e8f0] hover:bg-slate-50 hover:border-slate-300 transition-all text-sm text-[#1e293b]"
                  >
                    <a.icon size={16} className="text-[#64748b] shrink-0" />
                    <span className="flex-1">{a.label}</span>
                    {a.badge !== undefined && (
                      <span className="text-xs bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded-md border border-amber-200">{a.badge}</span>
                    )}
                    <ChevronRight size={14} className="text-[#e2e8f0]" />
                  </Link>
                ))}
              </div>

              {/* Reasoning log */}
              <div>
                <h3 className="text-sm font-semibold text-[#002147] mb-3">Reasoning Log</h3>
                {estimate.reasoning_log.length === 0 ? (
                  <p className="text-sm text-[#64748b]">No log entries.</p>
                ) : (
                  <div className="bg-slate-50 rounded-md border border-[#e2e8f0] p-4 max-h-80 overflow-y-auto">
                    {estimate.reasoning_log.map((entry, i) => (
                      <div key={i} className="text-xs text-[#1e293b] py-1.5 border-b border-[#e2e8f0] last:border-0 font-mono">
                        <span className="text-[#64748b] mr-3 select-none">{String(i + 1).padStart(3, '0')}</span>
                        {entry}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* VE Opportunities summary */}
              {estimate.ve_opportunities.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-[#002147]">VE Opportunities</h3>
                    <span className="text-xs font-mono text-[#059669]">Potential: {fmtAED(veTotal)}</span>
                  </div>
                  <div className="space-y-2">
                    {estimate.ve_opportunities.slice(0, 5).map((ve, i) => (
                      <div key={i} className="flex items-center justify-between text-sm p-3 bg-slate-50 rounded-md border border-[#e2e8f0]">
                        <span className="text-[#1e293b] truncate flex-1">{ve.description || ve.item_code}</span>
                        <span className="font-mono text-[#059669] text-xs ml-4 shrink-0">
                          -{(ve.saving_aed || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} AED
                        </span>
                      </div>
                    ))}
                    {estimate.ve_opportunities.length > 5 && (
                      <Link href={`/estimate/${id}/ve-menu`} className="text-xs text-[#002147] hover:underline">
                        +{estimate.ve_opportunities.length - 5} more opportunities
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* BOM TAB */}
          {activeTab === 'bom' && <BOMTable items={displayBomItems} />}

          {/* SCOPE TAB */}
          {activeTab === 'scope' && <ScopeTab scope={estimate.project_scope} openings={estimate.opening_schedule} />}

          {/* FINANCIAL TAB */}
          {activeTab === 'financial' && <FinancialTab financial={financial} boqSummary={boqSummary} bomSummary={estimate.bom_output?.summary} />}

          {/* ENGINEERING TAB */}
          {activeTab === 'engineering' && <EngineeringTab openings={openingsList} structural={estimate.structural_results} engineeringResults={engineeringResults} id={id as string} />}

          {/* COMPLIANCE TAB */}
          {activeTab === 'compliance' && <ComplianceTab structural={estimate.structural_results} id={id as string} />}

          {/* CUTTING LIST TAB */}
          {activeTab === 'cutting' && <CuttingListTab cuttingList={estimate.cutting_list} />}

          {/* DRAWINGS TAB */}
          {activeTab === 'drawings' && (
            <DrawingsTab estimateId={id as string} />
          )}
        </div>
      </div>

      {/* FINANCIAL SUMMARY FOOTER */}
      {totalContractValue !== undefined && (
        <div className="mt-4 bg-white rounded-md border border-[#e2e8f0] p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 print:mt-2 shadow-sm">
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-[#64748b]">Material</span>
              <span className="ml-2 font-mono font-medium text-[#1e293b]">{fmtAED(financial.material_cost_aed)}</span>
            </div>
            <div>
              <span className="text-[#64748b]">Labor</span>
              <span className="ml-2 font-mono font-medium text-[#1e293b]">{fmtAED(financial.labor_cost_aed)}</span>
            </div>
            {financial.gross_margin_pct !== undefined && (
              <div>
                <span className="text-[#64748b]">Margin</span>
                <span className="ml-2 font-mono font-medium text-[#059669]">{(financial.gross_margin_pct * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
          <div className="text-right">
            <span className="text-xs text-[#64748b] mr-3">Total Contract Value</span>
            <span className="text-lg font-bold font-mono text-[#002147]">{fmtAED(totalContractValue)}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default EstimatePage;
