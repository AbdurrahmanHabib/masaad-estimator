import React from 'react';
import ProjectIngestion from '../../components/ProjectIngestion';
import Link from 'next/link';
import { ChevronLeft } from 'lucide-react';

export default function NewEstimate() {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      {/* MINI SIDEBAR */}
      <div className="w-20 bg-slate-900 border-r border-slate-800 flex flex-col items-center py-8">
        <Link href="/" className="mb-12 hover:opacity-80 transition-all">
          <div className="w-10 h-10 bg-ms-emerald rounded-sm flex items-center justify-center font-black text-black text-xs shadow-lg shadow-emerald-500/20">MS</div>
        </Link>
        <Link href="/" className="p-3 text-slate-500 hover:text-white transition-colors">
          <ChevronLeft size={24} />
        </Link>
      </div>

      {/* CONTENT */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ProjectIngestion />
      </div>
    </div>
  );
}