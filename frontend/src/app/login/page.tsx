'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import Background from '@/components/ui/Background';

export default function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [code, setCode] = useState('');
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!loading && isAuthenticated) router.replace('/dashboard');
  }, [loading, isAuthenticated, router]);

  const submit = () => {
    if (login(code)) router.replace('/dashboard');
    else setErr("That access code isn't right — try again.");
  };

  return (
    <>
      <Background />
      <div id="login" style={{ display: 'flex' }}>
        <div className="logincard">
          <div className="dot">hp</div>
          <h1>RAD Intelligence Desk</h1>
          <p>Enter the access code to continue.</p>
          <input
            className="inp"
            type="password"
            placeholder="Access code"
            autoComplete="off"
            style={{ textAlign: 'center', fontFamily: 'var(--mono)' }}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            autoFocus
          />
          <div className="err">{err}</div>
          <button className="loginbtn" onClick={submit}>Enter</button>
        </div>
      </div>
    </>
  );
}
