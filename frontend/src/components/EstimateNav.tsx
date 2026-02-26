/**
 * Shared navigation component for estimate sub-pages.
 * Shows quick links to: Overview, Compliance, VE Menu, RFI Log, Approve
 */
import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import {
  LayoutDashboard, ShieldAlert, TrendingDown, MessageSquare, CheckCircle
} from 'lucide-react';

interface EstimateNavProps {
  estimateId: string;
  status?: string;
}

const navItems = (id: string) => [
  { label: 'Overview', href: `/estimate/${id}`, icon: LayoutDashboard },
  { label: 'Compliance', href: `/estimate/${id}/compliance`, icon: ShieldAlert },
  { label: 'VE Menu', href: `/estimate/${id}/ve-menu`, icon: TrendingDown },
  { label: 'RFI Log', href: `/estimate/${id}/rfi`, icon: MessageSquare },
  { label: 'Approve', href: `/estimate/${id}/approve`, icon: CheckCircle },
];

export default function EstimateNav({ estimateId, status }: EstimateNavProps) {
  const router = useRouter();

  return (
    <nav className="flex items-center gap-1 mb-6 bg-gray-900 border border-gray-700 rounded-xl p-1">
      {navItems(estimateId).map(({ label, href, icon: Icon }) => {
        const isActive = router.asPath === href;
        const isApprove = label === 'Approve';

        return (
          <Link key={href} href={href}>
            <span
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium cursor-pointer transition-all ${
                isActive
                  ? 'bg-blue-700 text-white'
                  : isApprove && status === 'REVIEW_REQUIRED'
                  ? 'bg-amber-900/40 text-amber-300 hover:bg-amber-900/60 border border-amber-700/50 animate-pulse'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              <Icon size={14} />
              {label}
              {isApprove && status === 'REVIEW_REQUIRED' && (
                <span className="w-2 h-2 rounded-full bg-amber-400 ml-1" />
              )}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
