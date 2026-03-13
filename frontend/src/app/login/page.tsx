'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import NetworkBackground from '@/components/ui/NetworkBackground';

export default function LoginPage() {
  const router = useRouter();
  const { isAuthenticated, loading, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [loading, isAuthenticated, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    // Brief delay for UX
    await new Promise((r) => setTimeout(r, 400));

    const success = login(email, password);
    if (success) {
      router.push('/dashboard');
    } else {
      setError('Invalid email or password. Please try again.');
      setIsSubmitting(false);
    }
  };

  if (loading || isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F4F4]">
        <svg className="w-8 h-8 text-[#939393] animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F4F4F4] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Network background */}
      <div className="fixed inset-0 pointer-events-none">
        <NetworkBackground className="w-full h-full text-[#282727]" opacity={0.04} />
      </div>

      {/* Login card */}
      <div className="relative z-10 w-full max-w-md animate-in">
        <div className="card p-8 sm:p-10">
          {/* Branding */}
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-primary-500 rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-[#282727] tracking-tight">RAD Admin Portal</h1>
            <p className="text-xs text-[#939393] tracking-widest uppercase mt-1">Intercept OS</p>
          </div>

          {/* Welcome text */}
          <div className="text-center mb-6">
            <h2 className="text-lg font-semibold text-[#282727]">Welcome back</h2>
            <p className="text-sm text-[#939393] mt-1">Sign in to access your intelligence dashboard.</p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[#282727] mb-1">
                Email
              </label>
              <input
                type="text"
                id="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(''); }}
                placeholder="admin@intercept"
                className="input-field"
                autoComplete="email"
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-[#282727] mb-1">
                Password
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(''); }}
                placeholder="Enter your password"
                className="input-field"
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !email || !password}
              className={`btn-primary w-full text-sm ${isSubmitting || !email || !password ? 'opacity-60 cursor-not-allowed' : ''}`}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Signing in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-[#939393] mt-6">
          Powered by 20 AI Specialists &middot; Intercept Group
        </p>
      </div>
    </div>
  );
}
