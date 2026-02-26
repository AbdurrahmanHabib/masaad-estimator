import React, { useState, useRef, useEffect } from 'react';
import { 
  Upload, 
  Users, 
  Briefcase, 
  TrendingUp, 
  Building2, 
  Calculator,
  ShieldCheck,
  Zap,
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

  // Load current rates on mount
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
          stock_length: 6.0 // default
        })
      });
      if (res.ok) alert("Market Variables Committed");
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-ms-dark space-y-6">
      <div className="flex items-center justify-between border-b border-ms-border pb-4">
        <div>
          <h2 className="text-xl font-black uppercase tracking-tighter text-ms-emerald italic">Mission_Control_Center</h2>
          <p className="text-[10px] text-slate-500 font-mono uppercase tracking-[0.2em]">Group_Financial_Architecture // SaaS_Admin</p>
        </div>
        <div className="flex gap-4">
          <div className="px-4 py-2 bg-ms-panel border border-ms-border rounded-sm text-right">
            <span className="block text-[7px] font-black text-slate-500 uppercase tracking-widest">Group_Global_Sync</span>
            <span className="text-xs font-mono text-ms-emerald font-black tracking-tighter">ESTABLISHED_✓</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* CONSOLIDATED GROUP PANEL */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-ms-panel border border-ms-border p-6 shadow-2xl relative overflow-hidden rounded-sm group hover:border-ms-emerald/30 transition-all">
            <div className="flex items-center justify-between mb-6 border-b border-ms-border pb-4">
              <div className="flex items-center gap-3">
                <Building2 size={18} className="text-ms-emerald" />
                <div>
                  <h3 className="text-xs font-black text-white uppercase tracking-widest">Consolidated_Group_Panel</h3>
                  <p className="text-[8px] text-slate-500 font-mono">Aggregating: MADINAT | AL JAZEERA | MADINAT AL JAZEERA</p>
                </div>
              </div>
              <div className="text-right">
                <span className="block text-[8px] font-black text-slate-500 uppercase">Total_Overhead_Pool</span>
                <span className="text-2xl font-mono text-white font-black tabular-nums tracking-tighter">
                  AED {activeRates.totalAdminPool.toLocaleString()}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* ZONE 1: PAYROLL */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                    <Users size={12} className="text-ms-emerald" /> Payroll_Engine
                  </h4>
                  <span className="text-[8px] font-mono text-ms-emerald bg-ms-emerald/5 px-2 py-0.5 rounded border border-ms-emerald/10">Filter: JOB_LOC=='FACTORY'</span>
                </div>
                <input type="file" ref={payrollInputRef} className="hidden" accept=".csv" onChange={(e) => handleFileUpload('payroll', e)} />
                <div 
                  onClick={() => !isUploading.payroll && payrollInputRef.current?.click()}
                  className="border border-ms-border border-dashed bg-ms-dark/50 p-6 text-center cursor-pointer hover:bg-ms-emerald/[0.02] hover:border-ms-emerald/50 transition-all rounded-sm group/upload"
                >
                  {isUploading.payroll ? <Loader2 size={20} className="mx-auto text-ms-emerald animate-spin mb-2" /> : <Upload size={20} className="mx-auto text-slate-600 mb-2 group-hover/upload:text-ms-emerald transition-colors" />}
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{isUploading.payroll ? 'Processing...' : 'Upload_Group_Payroll.csv'}</p>
                  <p className="text-[7px] text-slate-600 font-mono">ISO_9001 Validation Enabled</p>
                </div>
              </div>

              {/* ZONE 2: EXPENSES */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                    <Calculator size={12} className="text-ms-amber" /> Overhead_Matrix
                  </h4>
                  <span className="text-[8px] font-mono text-ms-amber bg-ms-amber/5 px-2 py-0.5 rounded border border-ms-amber/10">Action: SUM_ALL_COLUMNS</span>
                </div>
                <input type="file" ref={expensesInputRef} className="hidden" accept=".csv" onChange={(e) => handleFileUpload('expenses', e)} />
                <div 
                  onClick={() => !isUploading.expenses && expensesInputRef.current?.click()}
                  className="border border-ms-border border-dashed bg-ms-dark/50 p-6 text-center cursor-pointer hover:bg-ms-amber/[0.02] hover:border-ms-amber/50 transition-all rounded-sm group/upload"
                >
                  {isUploading.expenses ? <Loader2 size={20} className="mx-auto text-ms-amber animate-spin mb-2" /> : <Upload size={20} className="mx-auto text-slate-600 mb-2 group-hover/upload:text-ms-amber transition-colors" />}
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{isUploading.expenses ? 'Processing...' : 'Upload_Admin_Expenses.csv'}</p>
                  <p className="text-[7px] text-slate-600 font-mono">Precision: 4 Decimal Places</p>
                </div>
              </div>
            </div>
          </div>

          <CatalogUploader />
        </div>

        {/* FINANCIAL PRECISION COLUMN */}
        <div className="space-y-6">
          <div className="bg-ms-panel border border-ms-border p-6 rounded-sm shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-2 opacity-5">
              <Zap size={80} className="text-ms-emerald" />
            </div>
            <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2 mb-6 border-b border-ms-border pb-3 italic">
              <ShieldCheck size={14} className="text-ms-emerald" /> Real_Time_Metrics
            </h3>
            
            <div className="space-y-6">
              <div className="p-4 bg-ms-dark border border-ms-border rounded-sm group hover:border-ms-emerald/50 transition-all shadow-inner">
                <label className="block text-[8px] font-black text-slate-500 uppercase tracking-widest mb-3">True_Group_Shop_Rate</label>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-mono text-ms-emerald font-black tabular-nums tracking-tighter drop-shadow-[0_0_10px_#10b98120]">
                    {activeRates.trueShopRate.toFixed(2)}
                  </span>
                  <span className="text-xs font-bold text-slate-600 italic">AED/HR</span>
                </div>
                <div className="mt-4 flex justify-between items-center text-[7px] font-mono text-slate-500 uppercase border-t border-ms-border/50 pt-3">
                  <span>Factory_HC: {activeRates.factoryHeadcount}</span>
                  <span className="text-ms-emerald font-bold">Burden_Factor: 1.35x</span>
                </div>
              </div>

              <div className="space-y-4 pt-4">
                <div className="bg-ms-dark/40 border border-ms-border p-4 rounded-sm">
                  <label className="block text-[8px] font-black text-slate-500 uppercase tracking-widest mb-3 italic underline decoration-ms-emerald/30">Market_Volatility_Control</label>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-[7px] text-slate-500 uppercase font-bold tracking-widest">Live_LME_Alum_Rate (USD/MT)</span>
                      </div>
                      <input 
                        type="number" 
                        value={marketVars.lmeRate} 
                        onChange={(e) => setMarketVars({...marketVars, lmeRate: Number(e.target.value)})}
                        className="w-full bg-ms-dark border border-ms-border text-ms-emerald font-mono text-xs p-2.5 rounded-sm focus:outline-none focus:border-ms-emerald/50 transition-all" 
                      />
                    </div>
                    <div>
                      <span className="text-[7px] text-slate-500 uppercase font-bold block mb-1 tracking-widest">Billet_Premium (USD/MT)</span>
                      <input 
                        type="number" 
                        value={marketVars.billetPremium} 
                        onChange={(e) => setMarketVars({...marketVars, billetPremium: Number(e.target.value)})}
                        className="w-full bg-ms-dark border border-ms-border text-white font-mono text-xs p-2.5 rounded-sm focus:outline-none focus:border-ms-emerald/50 transition-all" 
                      />
                    </div>
                  </div>
                </div>

                <button 
                  onClick={commitMarketVars}
                  className="w-full py-3.5 bg-ms-slate-800 hover:bg-ms-emerald hover:text-black text-ms-emerald font-black uppercase text-[9px] tracking-[0.2em] transition-all rounded-sm border border-ms-emerald/20 hover:border-ms-emerald shadow-lg shadow-ms-emerald/5"
                >
                  Commit_Financial_Variables
                </button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}