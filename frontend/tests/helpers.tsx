import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { AuthProvider, type AuthState } from "../src/auth/AuthContext";

export function renderWithQueryClient(ui: ReactElement): RenderResult & {
  queryClient: QueryClient;
} {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  const result = render(ui, { wrapper });
  return { ...result, queryClient };
}

const OPERATOR_STATE: AuthState = {
  token: "test-token",
  role: "operator",
  username: "test-operator",
};

const VIEWER_STATE: AuthState = {
  token: "test-token",
  role: "viewer",
  username: "test-viewer",
};

/**
 * Like `renderWithQueryClient`, but also wraps the component in an
 * `AuthProvider` pre-seeded with a signed-in role — for components that
 * call `useAuth()` (anything role-gated). Defaults to "operator" so
 * existing happy-path tests keep working; pass "viewer" to test the
 * read-only gating instead.
 */
export function renderWithProviders(
  ui: ReactElement,
  { role = "operator" as "operator" | "viewer" } = {},
): RenderResult & { queryClient: QueryClient } {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
  const initialState = role === "operator" ? OPERATOR_STATE : VIEWER_STATE;
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider initialState={initialState}>{children}</AuthProvider>
    </QueryClientProvider>
  );
  const result = render(ui, { wrapper });
  return { ...result, queryClient };
}
