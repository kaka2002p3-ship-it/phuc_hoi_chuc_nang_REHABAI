import { createContext, useCallback, useContext, useState } from 'react';
import type { ReactNode } from 'react';

export type Role = 'admin' | 'doctor' | 'patient';
export type User = { id: string; email: string; full_name: string; phone?: string|null; bio?: string|null; avatar_data_url?: string|null; weekly_goal?: number|null; height_cm?: number|null; weight_kg?: number|null; role?: Role };
type AuthValue = { user: User | null; token: string | null; save: (token: string, user: User) => void; updateUser: (user: User) => void; logout: () => void };
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('rehabai_token'));
  const [user, setUser] = useState<User | null>(() => {
    try { return JSON.parse(localStorage.getItem('rehabai_user') || 'null'); } catch { return null; }
  });
  const save = useCallback((nextToken: string, nextUser: User) => {
    localStorage.setItem('rehabai_token', nextToken); localStorage.setItem('rehabai_user', JSON.stringify(nextUser));
    setToken(nextToken); setUser(nextUser);
  }, []);
  const updateUser = useCallback((nextUser: User) => { localStorage.setItem('rehabai_user', JSON.stringify(nextUser)); setUser(nextUser); }, []);
  const logout = useCallback(() => { localStorage.removeItem('rehabai_token'); localStorage.removeItem('rehabai_user'); setToken(null); setUser(null); }, []);
  return <AuthContext.Provider value={{ user, token, save, updateUser, logout }}>{children}</AuthContext.Provider>;
}

// oxlint-disable-next-line react/only-export-components -- provider hook intentionally colocated with its context
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('AuthProvider is missing');
  return value;
}
