'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  loading: boolean;
  /** Returns true when the access code is correct. */
  login: (code: string) => boolean;
  logout: () => void;
}

const AUTH_KEY = 'rad_authenticated';
// Single shared access code — case-insensitive, surrounding space tolerated.
const ACCESS_CODE = 'radical rad';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setIsAuthenticated(localStorage.getItem(AUTH_KEY) === 'true');
    setLoading(false);
  }, []);

  const login = (code: string): boolean => {
    if ((code || '').trim().toLowerCase() === ACCESS_CODE) {
      localStorage.setItem(AUTH_KEY, 'true');
      setIsAuthenticated(true);
      return true;
    }
    return false;
  };

  const logout = () => {
    localStorage.removeItem(AUTH_KEY);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
