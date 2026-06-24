'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

const NAV = [
  { name: 'Home', href: '/dashboard', icon: 'M3 11l9-8 9 8M5 10v10h14V10' },
  { name: 'Jobs', href: '/dashboard/jobs', icon: 'M3 5h18v14H3zM3 9h18' },
  { name: 'Sellers', href: '/dashboard/sellers', icon: 'M9 8a3 3 0 100 6 3 3 0 000-6zM3 20a6 6 0 0112 0M17 8a3 3 0 010 6M21 20a5 5 0 00-7-4.5' },
  { name: 'Content Audit', href: '/dashboard/content-audit', icon: 'M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6' },
  { name: 'Documentation', href: '/dashboard/docs', icon: 'M4 5a2 2 0 012-2h8l4 4v12a2 2 0 01-2 2H6a2 2 0 01-2-2zM9 8h4M9 12h6M9 16h6' },
];

export default function Rail() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useAuth();
  const active = (href: string) =>
    href === '/dashboard' ? pathname === '/dashboard' : pathname.startsWith(href);

  return (
    <aside className="rail">
      <div className="brand">
        <div className="dot">hp</div>
        <div><b>RADAR</b><small>Intelligence Ops</small></div>
      </div>
      <nav className="nav">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href} className={active(n.href) ? 'on' : ''}>
            <svg className="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}>
              <path d={n.icon} />
            </svg>
            {n.name}
          </Link>
        ))}
      </nav>
      <button className="signout" onClick={() => { logout(); router.replace('/login'); }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}>
          <path d="M16 17l5-5-5-5M21 12H9M9 3H6a2 2 0 00-2 2v14a2 2 0 002 2h3" />
        </svg>
        Sign out
      </button>
      <div className="foot">v3.1 · live<br />radportal.vercel.app</div>
    </aside>
  );
}
