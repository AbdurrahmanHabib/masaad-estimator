import React from 'react';
import Link from 'next/link';
import { 
  Briefcase, 
  TrendingUp, 
  Settings2, 
  Users, 
  Clock, 
  ChevronRight,
  Target,
  Zap,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';

export default function Dashboard() {
  const [lastSyncTime, setLastSyncTime] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLastSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  }, []);

  return (
    <div className="space-y-10">
      {/* WELCOME SECTION */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-800 uppercase tracking-tighter italic">Welcome back, Admin</h1>
          <p className="text-slate-500 font-medium text-sm mt-1">Here is what is happening with your estimations today.</p>
        </div>
        <div className="flex gap-3">
          <Link href="/estimate/new" className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-600/20 flex items-center gap-2">
            <Zap size={14} /> New Estimation
          </Link>
          <button className="px-6 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm">
            Generate Reports
          </button>
        </div>
      </div>

      {/* QUICK ACTIONS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-ms-border group hover:border-blue-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 mb-4 group-hover:scale-110 transition-transform">
            <Target size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Active Projects</h3>
          <p className="text-xs text-slate-500 mt-1">04 Live Estimations</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-ms-border group hover:border-emerald-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center text-emerald-600 mb-4 group-hover:scale-110 transition-transform">
            <TrendingUp size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Direct Cost Pool</h3>
          <p className="text-xs text-slate-500 mt-1">AED 1.2M Overhead</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-ms-border group hover:border-amber-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center text-amber-600 mb-4 group-hover:scale-110 transition-transform">
            <Zap size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Optimization Gain</h3>
          <p className="text-xs text-slate-500 mt-1">96.8% Efficiency</p>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-ms-border group hover:border-red-500 transition-all cursor-pointer">
          <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center text-red-600 mb-4 group-hover:scale-110 transition-transform">
            <AlertCircle size={24} />
          </div>
          <h3 className="font-bold text-slate-800">Pending Audits</h3>
          <p className="text-xs text-slate-500 mt-1">02 Requires Review</p>
        </div>
      </div>

      {/* KEY METRICS (VIBRANT CARDS) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="bg-gradient-to-br from-blue-600 to-blue-800 p-8 rounded-[2rem] shadow-xl shadow-blue-600/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Total Estimates</h3>
            <p className="text-5xl font-mono font-black tracking-tighter">90</p>
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              View All <ChevronRight size={12} />
            </div>
          </div>
          <Briefcase size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>

        <div className="bg-gradient-to-br from-emerald-500 to-emerald-700 p-8 rounded-[2rem] shadow-xl shadow-emerald-500/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Factory Margin</h3>
            <p className="text-5xl font-mono font-black tracking-tighter">24%</p>
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              View Margin Matrix <ChevronRight size={12} />
            </div>
          </div>
          <Target size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>

        <div className="bg-gradient-to-br from-red-500 to-red-700 p-8 rounded-[2rem] shadow-xl shadow-red-500/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Technical RFIs</h3>
            <p className="text-5xl font-mono font-black tracking-tighter">02</p>
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              Resolve Issues <ChevronRight size={12} />
            </div>
          </div>
          <ShieldCheck size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>

        <div className="bg-gradient-to-br from-amber-500 to-amber-600 p-8 rounded-[2rem] shadow-xl shadow-amber-500/20 text-white relative overflow-hidden group hover:scale-[1.02] transition-all">
          <div className="relative z-10">
            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 mb-2">Optimization Gaps</h3>
            <p className="text-5xl font-mono font-black tracking-tighter">05</p>
            <div className="mt-8 flex items-center gap-2 text-[10px] font-bold bg-white/10 w-fit px-3 py-1 rounded-full">
              Review Gaps <ChevronRight size={12} />
            </div>
          </div>
          <Zap size={120} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
        </div>
      </div>

      {/* PROJECT DEPLOYMENT QUEUE */}
      <div className="bg-white border border-ms-border rounded-2xl shadow-sm overflow-hidden">
        <div className="p-6 border-b border-ms-border bg-slate-50/50 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-2 h-6 bg-blue-600 rounded-full"></div>
            <h3 className="text-sm font-black uppercase tracking-widest text-slate-800 italic">Project_Deployment_Queue</h3>
          </div>
          <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            <Clock size={14} /> Last Sync: {lastSyncTime || '...'}
          </div>
        </div>
        
        <table className="w-full text-left">
          <thead className="bg-slate-50 text-slate-400 uppercase text-[9px] font-black tracking-widest border-b border-ms-border">
            <tr>
              <th className="px-8 py-4">Project_Ref</th>
              <th className="px-8 py-4">Primary_Client</th>
              <th className="px-8 py-4">Region</th>
              <th className="px-8 py-4">Status</th>
              <th className="px-8 py-4 text-right">Verification</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-sans text-xs">
            <tr className="hover:bg-blue-50/30 transition-colors group">
              <td className="px-8 py-5 font-black text-blue-600">PRJ-KAB-001</td>
              <td className="px-8 py-5 text-slate-700 font-bold uppercase tracking-tight italic">Al Kabir Tower</td>
              <td className="px-8 py-5 text-slate-500 uppercase text-[10px] font-medium tracking-tighter">Kabul_Afghanistan</td>
              <td className="px-8 py-5">
                <span className="px-3 py-1 bg-emerald-100 text-emerald-600 border border-emerald-200 text-[9px] font-black uppercase tracking-widest rounded-full shadow-sm">In_Quantification</span>
              </td>
              <td className="px-8 py-5 text-right">
                <Link href="/estimate/PRJ-KAB-001" className="text-[10px] bg-slate-800 hover:bg-blue-600 text-white px-5 py-2 rounded-xl transition-all uppercase font-black tracking-widest shadow-lg shadow-blue-600/10">
                  Launch_Audit
                </Link>
              </td>
            </tr>
            <tr className="hover:bg-blue-50/30 transition-colors opacity-60">
              <td className="px-8 py-5 text-slate-400">PRJ-DXB-042</td>
              <td className="px-8 py-5 text-slate-400 font-bold uppercase tracking-tight italic">Dubai Hills Villa</td>
              <td className="px-8 py-5 text-slate-400 uppercase text-[10px] font-medium">Dubai_UAE</td>
              <td className="px-8 py-5">
                <span className="px-3 py-1 bg-slate-100 text-slate-400 text-[9px] font-bold uppercase tracking-widest rounded-full">Completed</span>
              </td>
              <td className="px-8 py-5 text-right">
                <button className="text-[10px] text-slate-400 font-black uppercase tracking-widest cursor-not-allowed">Archive_Only</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}