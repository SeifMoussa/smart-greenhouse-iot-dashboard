import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { setAuthToken } from "../api/client";
import { api } from "../api/endpoints";
import type { Role } from "../types/api";

export interface AuthState {
  token: string | null;
  role: Role | null;
  username: string | null;
}

export interface AuthContextValue extends AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const EMPTY_STATE: AuthState = { token: null, role: null, username: null };

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Holds the current user's JWT and role in memory only — never
 * localStorage/sessionStorage. A page refresh logs the user out; that's a
 * deliberate tradeoff to keep the token out of any storage an XSS payload
 * could read after the fact.
 */
export function AuthProvider({
  children,
  initialState,
}: {
  children: ReactNode;
  /** Test-only escape hatch to seed a signed-in state without a real login call. */
  initialState?: AuthState;
}) {
  const [state, setState] = useState<AuthState>(initialState ?? EMPTY_STATE);

  const login = useCallback(async (username: string, password: string) => {
    const response = await api.login(username, password);
    setAuthToken(response.access_token);
    setState({ token: response.access_token, role: response.role, username: response.username });
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    setState(EMPTY_STATE);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, isAuthenticated: state.token !== null, login, logout }),
    [state, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- context + hook belong together
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
