'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import NetworkBackground from '@/components/ui/NetworkBackground';
import { useAuth } from '@/lib/auth';

interface NavItem {
  name: string;
  href: string;
  icon: React.ReactNode;
}

const navigation: NavItem[] = [
  {
    name: 'Home',
    href: '/dashboard',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    name: 'Jobs',
    href: '/dashboard/jobs',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
  {
    name: 'Sellers',
    href: '/dashboard/sellers',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
  },
  {
    name: 'Content Audit',
    href: '/dashboard/content-audit',
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();

  const isActive = (href: string) => {
    if (href === '/dashboard') {
      return pathname === '/dashboard';
    }
    return pathname.startsWith(href);
  };

  const handleSignOut = () => {
    logout();
    router.push('/login');
  };

  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-56 bg-[#1a1a1a] text-white flex flex-col overflow-hidden">
      {/* Network pattern */}
      <div className="absolute inset-0 pointer-events-none">
        <NetworkBackground className="w-full h-full text-white" opacity={0.04} />
      </div>

      {/* Logo */}
      <div className="relative z-10 flex items-center h-16 px-4 border-b border-white/10">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 bg-primary-500 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <span className="text-sm font-bold tracking-tight block leading-tight">RAD Admin Portal</span>
            <span className="text-[10px] text-[#939393] tracking-widest uppercase">Intercept OS</span>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex-1 px-3 py-4 space-y-0.5">
        {navigation.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`group flex items-center px-3 py-2.5 rounded-lg transition-all duration-150 ${
                active
                  ? 'bg-white text-[#1a1a1a]'
                  : 'text-[#939393] hover:bg-white/5 hover:text-white'
              }`}
            >
              <span className={active ? 'text-primary-500' : 'text-[#939393] group-hover:text-white'}>
                {item.icon}
              </span>
              <span className="ml-3 text-sm font-medium">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="relative z-10 px-3 py-3 border-t border-white/10">
        {/* Sign Out */}
        <button
          onClick={handleSignOut}
          className="group flex items-center w-full px-3 py-2 mb-1 rounded-lg text-[#939393] hover:bg-white/5 hover:text-white transition-all duration-150"
        >
          <svg className="w-5 h-5 text-[#939393] group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span className="ml-3 text-sm font-medium">Sign Out</span>
        </button>

        {/* LLM Council */}
        <div className="flex items-center space-x-2.5 px-3 py-2">
          <div className="w-6 h-6 rounded bg-white/10 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-[#939393]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <p className="text-xs font-medium text-[#939393]">LLM Council</p>
            <p className="text-[10px] text-white/30">20 AI Specialists</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
