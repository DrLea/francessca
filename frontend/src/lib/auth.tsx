"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, getToken, setToken, type User } from "@/lib/api";

interface AuthState {
  user: User | null;
  loading: boolean;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await api.me());
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signIn = useCallback(
    async (token: string) => {
      setToken(token);
      await refresh();
    },
    [refresh],
  );

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** Where an account lands after signing in: lawyers and clients each have
 *  their own side of the app. */
export function homeFor(user: Pick<User, "role">): string {
  return user.role === "lawyer" ? "/lawyer" : "/dashboard";
}

/** Guard for the client pages. Redirects to /login when signed out, and
 *  sends a lawyer account to the lawyer portal — the two sides are kept
 *  apart. `user` stays null until the guard has passed. */
export function useRequireAuth() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const allowed = !!user && user.role !== "lawyer";
  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (!allowed) router.replace("/lawyer");
  }, [loading, user, allowed, router]);
  return { user: allowed ? user : null, loading };
}

/** Guard for the lawyer portal and the admin pages. */
export function useRequireRole(role: "lawyer" | "admin") {
  const { user, loading } = useAuth();
  const router = useRouter();
  const allowed = !!user && user.role === role;
  useEffect(() => {
    if (loading) return;
    if (!user) router.replace(role === "lawyer" ? "/lawyer/login" : "/login");
    else if (!allowed) router.replace(homeFor(user));
  }, [loading, user, allowed, role, router]);
  return { user: allowed ? user : null, loading };
}
