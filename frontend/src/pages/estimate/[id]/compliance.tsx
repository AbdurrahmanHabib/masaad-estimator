/**
 * Compliance Report Dashboard -- Phase 3B
 * C1: Structural check results (BS 6399-2)
 * C2: Thermal / Acoustic pass/fail (ASHRAE 90.1 + Dubai GBR)
 * C3: Fire & Life Safety matrix (UAE Civil Defence)
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { CheckCircle, XCircle, AlertTriangle, Loader2, ShieldAlert, Wind, Thermometer, Flame, ArrowLeft } from 'lucide-react';
import { apiGet } from '../../../lib/api';

interface StructuralCheck {
  profile_ref: string;
  span_mm: number;
  deflection_actual_mm: number;
  deflection_allowable_mm: number;
  utilisation_ratio: number;
  passed: boolean;
  note: string;
}

interface ThermalCheck {
  u_value_w_m2k: number | null;
  shgc: number | null;
  vlt: number | null;
  acoustic_rw_db: number | null;
  overall_passed: boolean;
  gaps: string[];
  notes: string[];
}

interface FireCheck {
  building_type: string;
  required_minutes: number;
  provided_minutes: number | null;
  passed: boolean;
  rfi_required: boolean;
}

interface ComplianceReport {
  overall_passed: boolean | null;
  summary_flags: string[];
  rfi_items: string[];
  structural: StructuralCheck[];
  thermal_acoustic: ThermalCheck;
  fire_safety: FireCheck;
}

const PassBadge = ({ passed }: { passed: boolean | null }) => {
  if (passed === null) return <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-xs rounded border border-slate-200">N/A</span>;
  return passed
    ? <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-50 text-green-700 text-xs rounded border border-green-200"><CheckCircle size={10} />PASS</span>
    : <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 text-red-700 text-xs rounded border border-red-200"><XCircle size={10} />FAIL</span>;
};

export default function CompliancePage() {
  const router = useRouter();
  const { id } = router.query;
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setNotFound(false);

    apiGet<ComplianceReport>(`/api/commercial/${id}/compliance`)
      .then(setReport)
      .catch((e) => {
        const msg = e.message || '';
        if (msg.includes('404') || msg.includes('not found') || msg.includes('Not Found')) {
          setNotFound(true);
        } else {
          setError(msg);
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="animate-spin text-slate-400" size={28} />
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-3">
          <ShieldAlert size={36} className="mx-auto text-slate-300" />
          <p className="text-slate-600 font-medium">No compliance data available</p>
          <p className="text-xs text-slate-400">Compliance checks have not been run for this estimate yet.</p>
          <Link href={`/estimate/${id}`} className="text-sm text-blue-600 hover:underline inline-block mt-2">
            Back to Estimate
          </Link>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="text-center space-y-3">
          <AlertTriangle size={36} className="mx-auto text-red-400" />
          <p className="text-slate-600 font-medium">Failed to load compliance report</p>
          <p className="text-xs text-red-500 max-w-md">{error}</p>
          <Link href={`/estimate/${id}`} className="text-sm text-blue-600 hover:underline inline-block mt-2">
            Back to Estimate
          </Link>
        </div>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/estimate/${id}`} className="p-1.5 hover:bg-slate-100 rounded-md transition-colors">
            <ArrowLeft size={18} className="text-slate-400" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <ShieldAlert size={20} className="text-blue-600" />
              Compliance Engineering Report
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Estimate: {typeof id === 'string' ? id.slice(0, 12) : id}
            </p>
          </div>
        </div>
        <PassBadge passed={report.overall_passed} />
      </div>

      {/* Summary Flags */}
      {report.summary_flags.length > 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <h3 className="text-amber-800 font-semibold text-sm mb-2 flex items-center gap-2">
            <AlertTriangle size={14} /> Compliance Flags ({report.summary_flags.length})
          </h3>
          <ul className="space-y-1">
            {report.summary_flags.map((flag, i) => (
              <li key={i} className="text-amber-700 text-sm">{flag}</li>
            ))}
          </ul>
        </div>
      )}

      {/* RFI Items */}
      {report.rfi_items.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <h3 className="text-red-800 font-semibold text-sm mb-2 flex items-center gap-2">
            <Flame size={14} /> Auto-Generated RFIs ({report.rfi_items.length})
          </h3>
          {report.rfi_items.map((rfi, i) => (
            <pre key={i} className="text-red-700 text-xs font-mono whitespace-pre-wrap mb-2 last:mb-0 bg-white/50 p-3 rounded border border-red-100">
              {rfi}
            </pre>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* C1: Structural */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Wind size={16} className="text-blue-600" />
            C1 -- Structural (BS 6399-2 / L/175)
          </h2>
          {report.structural.length === 0 ? (
            <p className="text-slate-400 text-sm">No aluminum profiles checked (BOM may be empty)</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="text-left py-2 px-3 font-semibold text-slate-600 text-xs">Profile</th>
                    <th className="text-right py-2 px-3 font-semibold text-slate-600 text-xs">Span (mm)</th>
                    <th className="text-right py-2 px-3 font-semibold text-slate-600 text-xs">Actual d</th>
                    <th className="text-right py-2 px-3 font-semibold text-slate-600 text-xs">Allow d</th>
                    <th className="text-right py-2 px-3 font-semibold text-slate-600 text-xs">UR</th>
                    <th className="text-center py-2 px-3 font-semibold text-slate-600 text-xs">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {report.structural.map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50/50">
                      <td className="py-2 px-3 font-mono text-xs text-slate-700">{r.profile_ref}</td>
                      <td className="py-2 px-3 text-right font-mono">{r.span_mm.toFixed(0)}</td>
                      <td className={`py-2 px-3 text-right font-mono ${r.passed ? 'text-green-600' : 'text-red-600'}`}>
                        {r.deflection_actual_mm.toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-right font-mono text-slate-500">{r.deflection_allowable_mm.toFixed(2)}</td>
                      <td className={`py-2 px-3 text-right font-mono font-medium ${r.utilisation_ratio <= 1 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.utilisation_ratio.toFixed(3)}
                      </td>
                      <td className="py-2 px-3 text-center">
                        <PassBadge passed={r.passed} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* C2 + C3 side panel */}
        <div className="space-y-4">
          {/* C2: Thermal/Acoustic */}
          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <Thermometer size={14} className="text-cyan-600" />
              C2 -- Thermal / Acoustic
            </h2>
            <div className="space-y-2 text-sm">
              {[
                ['U-value', report.thermal_acoustic.u_value_w_m2k !== null ? `${report.thermal_acoustic.u_value_w_m2k} W/m2K` : '--'],
                ['SHGC', report.thermal_acoustic.shgc ?? '--'],
                ['VLT', report.thermal_acoustic.vlt ?? '--'],
                ['Rw', report.thermal_acoustic.acoustic_rw_db !== null ? `${report.thermal_acoustic.acoustic_rw_db} dB` : '--'],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between items-center">
                  <span className="text-slate-500">{label as string}</span>
                  <span className="font-mono text-slate-700">{String(value)}</span>
                </div>
              ))}
              <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                <span className="font-medium text-slate-700">Overall</span>
                <PassBadge passed={report.thermal_acoustic.overall_passed} />
              </div>
            </div>
            {report.thermal_acoustic.gaps.length > 0 && (
              <div className="mt-3 space-y-1">
                {report.thermal_acoustic.gaps.map((g, i) => (
                  <p key={i} className="text-red-600 text-xs">Warning: {g}</p>
                ))}
              </div>
            )}
          </div>

          {/* C3: Fire Safety */}
          <div className="bg-white border border-slate-200 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <Flame size={14} className="text-orange-500" />
              C3 -- Fire & Life Safety
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Building type</span>
                <span className="capitalize text-slate-700">{report.fire_safety.building_type.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Required FRL</span>
                <span className="font-mono text-slate-700">{report.fire_safety.required_minutes} min</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Provided FRL</span>
                <span className="font-mono text-slate-700">{report.fire_safety.provided_minutes !== null ? `${report.fire_safety.provided_minutes} min` : 'Not specified'}</span>
              </div>
              <div className="pt-2 border-t border-slate-200 flex justify-between items-center">
                <span className="font-medium text-slate-700">Status</span>
                <PassBadge passed={report.fire_safety.passed} />
              </div>
            </div>
            {report.fire_safety.rfi_required && (
              <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">
                RFI auto-generated -- review RFI log
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
