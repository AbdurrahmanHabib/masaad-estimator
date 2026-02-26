import React, { useState, useRef, useEffect } from 'react';
import {
  Upload,
  Users,
  Building2,
  Calculator,
  ShieldCheck,
  Loader2
} from 'lucide-react';
import CatalogUploader from '../../components/Settings/CatalogUploader';

export default function SettingsDashboard() {
  const [marketVars, setMarketVars] = useState({ lmeRate: 2450.00, billetPremium: 450.00 });
  const [activeRates, setActiveRates] = useState({
    trueShopRate: 48.75,
    totalAdminPool: 1245000,
    factoryHeadcount: 142
  });
  const [isUploading, setIsUploading] = useState<{payroll?: boolean, expenses?: boolean}>({});

  const payrollInputRef = useRef<HTMLInputElement>(null);
  const expensesInputRef = useRef<HTMLInputElement>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetch(`${API_URL}/api/settings/current-rates`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data) return;
        if (data.lme_aluminum_usd_mt) setMarketVars(prev => ({ ...prev, lmeRate: data.lme_aluminum_usd_mt }));
        if (data.baseline_labor_burn_rate_aed) {
          setActiveRates(prev => ({ ...prev, trueShopRate: data.baseline_labor_burn_rate_aed }));
        }
      })
      .catch(() => {});
  }, [API_URL]);

  const handleFileUpload = async (type: 'payroll' | 'expenses', e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(prev => ({ ...prev, [type]: true }));
    const formData = new FormData();
    formData.append('file', file);

    try {
      const endpoint = type === 'payroll' ? '/api/settings/upload-payroll' : '/api/settings/upload-expenses';
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) throw new Error(`${type} upload failed`);
      const data = await res.json();

      if (type === 'payroll') {
        setActiveRates(prev => ({
          ...prev,
          trueShopRate: data.metrics.true_shop_rate_aed,
          factoryHeadcount: data.metrics.factory_headcount
        }));
      } else {
        setActiveRates(prev => ({
          ...prev,
          totalAdminPool: data.total_group_overhead_aed
        }));
      }
      alert(`${type.toUpperCase()} Processed Successfully`);
    } catch (err) {
      console.error(err);
      alert(`Error processing ${type}`);
    } finally {
      setIsUploading(prev => ({ ...prev, [type]: false }));
    }
  };

  const commitMarketVars = async () => {
    try {
      const res = await fetch(`${API_URL}/api/settings/update-market`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lme_rate: marketVars.lmeRate,
          billet_premium: marketVars.billetPremium,
          stock_length: 6.0
        })
      });
      if (res.ok) alert("Market Variables Committed");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between pb-4 border-b border-[#e2e8f0]">
        <div>
          <h2 className="text-xl font-bold text-[#002147]">Settings</h2>
          <p className="text-sm text-[#64748b] mt-0.5">Group financial architecture and system configuration.</p>
        </div>
        <div className="flex gap-3">
          <div className="px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-md text-right">
            <span className="block text-[10px] font-semibold text-emerald-600 uppercase tracking-wider">System Status</span>
            <span className="text-xs font-mono text-emerald-700 font-semibold">Connected</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* CONSOLIDATED GROUP PANEL */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white border border-[#e2e8f0] p-6 shadow-sm rounded-md">
            <div className="flex items-center justify-between mb-6 border-b border-[#e2e8f0] pb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-blue-50 rounded-md flex items-center justify-center">
                  <Building2 size={17} className="text-[#002147]" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[#002147]">Consolidated Group Panel</h3>
                  <p className="text-[10px] text-[#64748b]">Madinat Al Saada | Al Jazeera | Madinat Al Jazeera</p>
                </div>
              </div>
              <div className="text-right">
                <span className="block text-[10px] font-semibold text-[#64748b] uppercase tracking-wider">Total Overhead Pool</span>
                <span className="text-xl font-mono text-[#002147] font-bold tabular-nums">
                  AED {activeRates.totalAdminPool.toLocaleString()}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* ZONE 1: PAYROLL */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-[#002147] flex items-center gap-2">
                    <Users size={13} className="text-[#002147]" /> Payroll Engine
                  </h4>
                  <span className="text-[10px] font-mono text-[#002147] bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200">JOB_LOC = FACTORY</span>
                </div>
                <input type="file" ref={payrollInputRef} className="hidden" accept=".csv,.xlsx,.xls" onChange={(e) => handleFileUpload('payroll', e)} />
                <div
                  onClick={() => !isUploading.payroll && payrollInputRef.current?.click()}
                  className="border-2 border-dashed border-[#002147]/30 bg-slate-50 p-6 text-center cursor-pointer hover:bg-blue-50/50 hover:border-[#002147] transition-all rounded-md group"
                >
                  {isUploading.payroll ? (
                    <Loader2 size={20} className="mx-auto text-[#002147] animate-spin mb-2" />
                  ) : (
                    <Upload size={20} className="mx-auto text-[#64748b] mb-2 group-hover:text-[#002147] transition-colors" />
                  )}
                  <p className="text-xs font-semibold text-[#1e293b] mb-0.5">
                    {isUploading.payroll ? 'Processing...' : 'Upload Group Payroll'}
                  </p>
                  <p className="text-[10px] text-[#64748b]">.xlsx or .csv format</p>
                </div>
              </div>

              {/* ZONE 2: EXPENSES */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-[#002147] flex items-center gap-2">
                    <Calculator size={13} className="text-[#d97706]" /> Overhead Matrix
                  </h4>
                  <span className="text-[10px] font-mono text-[#d97706] bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">SUM ALL COLUMNS</span>
                </div>
                <input type="file" ref={expensesInputRef} className="hidden" accept=".csv,.xlsx,.xls" onChange={(e) => handleFileUpload('expenses', e)} />
                <div
                  onClick={() => !isUploading.expenses && expensesInputRef.current?.click()}
                  className="border-2 border-dashed border-[#002147]/30 bg-slate-50 p-6 text-center cursor-pointer hover:bg-amber-50/50 hover:border-[#d97706] transition-all rounded-md group"
                >
                  {isUploading.expenses ? (
                    <Loader2 size={20} className="mx-auto text-[#d97706] animate-spin mb-2" />
                  ) : (
                    <Upload size={20} className="mx-auto text-[#64748b] mb-2 group-hover:text-[#d97706] transition-colors" />
                  )}
                  <p className="text-xs font-semibold text-[#1e293b] mb-0.5">
                    {isUploading.expenses ? 'Processing...' : 'Upload Admin Expenses'}
                  </p>
                  <p className="text-[10px] text-[#64748b]">.xlsx or .csv format</p>
                </div>
              </div>
            </div>
          </div>

          <CatalogUploader />
        </div>

        {/* FINANCIAL PRECISION COLUMN */}
        <div className="space-y-6">
          <div className="bg-white border border-[#e2e8f0] p-6 rounded-md shadow-sm">
            <h3 className="text-xs font-bold text-[#002147] uppercase tracking-wider flex items-center gap-2 mb-6 border-b border-[#e2e8f0] pb-3">
              <ShieldCheck size={14} className="text-[#059669]" /> Real-Time Metrics
            </h3>

            <div className="space-y-5">
              {/* Shop Rate */}
              <div className="p-4 bg-slate-50 border border-[#e2e8f0] rounded-md">
                <label className="block text-[10px] font-semibold text-[#64748b] uppercase tracking-wider mb-2">True Group Shop Rate</label>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-mono text-[#002147] font-bold tabular-nums">
                    {activeRates.trueShopRate.toFixed(2)}
                  </span>
                  <span className="text-xs font-semibold text-[#64748b]">AED/HR</span>
                </div>
                <div className="mt-3 flex justify-between items-center text-[10px] text-[#64748b] border-t border-[#e2e8f0] pt-2">
                  <span>Factory HC: {activeRates.factoryHeadcount}</span>
                  <span className="text-[#059669] font-semibold">Burden: 1.35x</span>
                </div>
              </div>

              {/* Market Variables */}
              <div className="space-y-4">
                <div className="bg-slate-50 border border-[#e2e8f0] p-4 rounded-md">
                  <label className="block text-[10px] font-semibold text-[#002147] uppercase tracking-wider mb-3">Market Variables</label>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-[10px] text-[#64748b] font-medium">LME Aluminium Rate (USD/MT)</span>
                      </div>
                      <input
                        type="number"
                        value={marketVars.lmeRate}
                        onChange={(e) => setMarketVars({...marketVars, lmeRate: Number(e.target.value)})}
                        className="w-full bg-white border border-[#e2e8f0] text-[#1e293b] font-mono text-sm p-2.5 rounded-md focus:outline-none focus:ring-2 focus:ring-[#002147]/20 focus:border-[#002147] transition-all"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-[#64748b] font-medium block mb-1">Billet Premium (USD/MT)</span>
                      <input
                        type="number"
                        value={marketVars.billetPremium}
                        onChange={(e) => setMarketVars({...marketVars, billetPremium: Number(e.target.value)})}
                        className="w-full bg-white border border-[#e2e8f0] text-[#1e293b] font-mono text-sm p-2.5 rounded-md focus:outline-none focus:ring-2 focus:ring-[#002147]/20 focus:border-[#002147] transition-all"
                      />
                    </div>
                  </div>
                </div>

                <button
                  onClick={commitMarketVars}
                  className="w-full py-3 bg-[#002147] hover:bg-[#1e3a5f] text-white font-semibold text-xs uppercase tracking-wider transition-all rounded-md"
                >
                  Commit Financial Variables
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
