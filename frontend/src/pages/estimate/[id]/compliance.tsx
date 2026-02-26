/**
 * Compliance Report Dashboard — Phase 3B
 * C1: Structural check results (BS 6399-2)
 * C2: Thermal / Acoustic pass/fail (ASHRAE 90.1 + Dubai GBR)
 * C3: Fire & Life Safety matrix (UAE Civil Defence)
 */
import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { CheckCircle, XCircle, AlertTriangle, Loader, ShieldAlert, Wind, Thermometer, Flame } from 'lucide-react';
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
  if (passed === null) return <span className="px-2 py-0.5 bg-gray-700 text-gray-400 text-xs rounded-full">N/A</span>;
  return passed
    ? <span className="px-2 py-0.5 bg-green-900/50 text-green-300 text-xs rounded-full border border-green-700 flex items-center gap-1"><CheckCircle size={10} />PASS</span>
    : <span className="px-2 py-0.5 bg-red-900/50 text-red-300 text-xs rounded-full border border-red-700 flex items-center gap-1"><XCircle size={10} />FAIL</span>;
};

export default function CompliancePage() {
  const router = useRouter();
  const { id } = router.query;
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    apiGet<ComplianceReport>(`/api/commercial/${id}/compliance`)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <Loader className="animate-spin text-blue-400" size={32} />
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-red-400 text-center">
        <XCircle size={48} className="mx-auto mb-3" />
        <p>{error}</p>
      </div>
    </div>
  );

  if (!report) return null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="text-blue-400" size={24} />
            Compliance Engineering Report
          </h1>
          <p className="text-gray-400 text-sm mt-1">Estimate: {typeof id === 'string' ? id.slice(0, 8) : id}...</p>
        </div>
        <PassBadge passed={report.overall_passed} />
      </div>

      {/* Summary Flags */}
      {report.summary_flags.length > 0 && (
        <div className="mb-6 p-4 bg-amber-900/20 border border-amber-700/40 rounded-xl">
          <h3 className="text-amber-300 font-semibold mb-2 flex items-center gap-2">
            <AlertTriangle size={16} /> Compliance Flags ({report.summary_flags.length})
          </h3>
          <ul className="space-y-1">
            {report.summary_flags.map((flag, i) => (
              <li key={i} className="text-amber-200 text-sm font-mono">{flag}</li>
            ))}
          </ul>
        </div>
      )}

      {/* RFI Items */}
      {report.rfi_items.length > 0 && (
        <div className="mb-6 p-4 bg-red-900/20 border border-red-700/40 rounded-xl">
          <h3 className="text-red-300 font-semibold mb-2 flex items-center gap-2">
            <Flame size={16} /> Auto-Generated RFIs ({report.rfi_items.length})
          </h3>
          {report.rfi_items.map((rfi, i) => (
            <pre key={i} className="text-red-200 text-xs font-mono whitespace-pre-wrap mb-3 last:mb-0 bg-gray-950/50 p-3 rounded">
              {rfi}
            </pre>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* C1: Structural */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Wind size={18} className="text-blue-400" />
            C1 — Structural (BS 6399-2 / L/175)
          </h2>
          {report.structural.length === 0 ? (
            <p className="text-gray-500 text-sm">No aluminum profiles checked (BOM may be empty)</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-xs border-b border-gray-700">
                    <th className="text-left py-2 pr-4">Profile</th>
                    <th className="text-right py-2 pr-4">Span (mm)</th>
                    <th className="text-right py-2 pr-4">Actual δ</th>
                    <th className="text-right py-2 pr-4">Allow δ</th>
                    <th className="text-right py-2 pr-4">UR</th>
                    <th className="text-center py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {report.structural.map((r, i) => (
                    <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/30">
                      <td className="py-2 pr-4 font-mono text-xs text-gray-300">{r.profile_ref}</td>
                      <td className="py-2 pr-4 text-right">{r.span_mm.toFixed(0)}</td>
                      <td className={`py-2 pr-4 text-right font-mono ${r.passed ? 'text-green-400' : 'text-red-400'}`}>
                        {r.deflection_actual_mm.toFixed(2)}
                      </td>
                      <td className="py-2 pr-4 text-right text-gray-400">{r.deflection_allowable_mm.toFixed(2)}</td>
                      <td className={`py-2 pr-4 text-right font-bold ${r.utilisation_ratio <= 1 ? 'text-green-400' : 'text-red-400'}`}>
                        {r.utilisation_ratio.toFixed(3)}
                      </td>
                      <td className="py-2 text-center">
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
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
            <h2 className="text-base font-bold mb-3 flex items-center gap-2">
              <Thermometer size={16} className="text-cyan-400" />
              C2 — Thermal / Acoustic
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">U-value</span>
                <span className="font-mono">
                  {report.thermal_acoustic.u_value_w_m2k !== null
                    ? `${report.thermal_acoustic.u_value_w_m2k} W/m²K`
                    : '—'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">SHGC</span>
                <span className="font-mono">{report.thermal_acoustic.shgc ?? '—'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">VLT</span>
                <span className="font-mono">{report.thermal_acoustic.vlt ?? '—'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Rw</span>
                <span className="font-mono">{report.thermal_acoustic.acoustic_rw_db !== null ? `${report.thermal_acoustic.acoustic_rw_db} dB` : '—'}</span>
              </div>
              <div className="pt-2 border-t border-gray-700 flex justify-between items-center">
                <span className="font-medium">Overall</span>
                <PassBadge passed={report.thermal_acoustic.overall_passed} />
              </div>
            </div>
            {report.thermal_acoustic.gaps.length > 0 && (
              <div className="mt-3 space-y-1">
                {report.thermal_acoustic.gaps.map((g, i) => (
                  <p key={i} className="text-red-400 text-xs">⚠ {g}</p>
                ))}
              </div>
            )}
          </div>

          {/* C3: Fire Safety */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
            <h2 className="text-base font-bold mb-3 flex items-center gap-2">
              <Flame size={16} className="text-orange-400" />
              C3 — Fire & Life Safety
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Building type</span>
                <span className="capitalize text-gray-300">{report.fire_safety.building_type.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Required FRL</span>
                <span className="font-mono">{report.fire_safety.required_minutes} min</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Provided FRL</span>
                <span className="font-mono">{report.fire_safety.provided_minutes !== null ? `${report.fire_safety.provided_minutes} min` : 'Not specified'}</span>
              </div>
              <div className="pt-2 border-t border-gray-700 flex justify-between items-center">
                <span className="font-medium">Status</span>
                <PassBadge passed={report.fire_safety.passed} />
              </div>
            </div>
            {report.fire_safety.rfi_required && (
              <div className="mt-3 p-2 bg-red-900/20 border border-red-700/40 rounded text-red-300 text-xs">
                RFI auto-generated — review RFI log
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
