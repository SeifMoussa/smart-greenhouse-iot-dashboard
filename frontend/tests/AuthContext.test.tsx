import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "../src/auth/AuthContext";
import { getAuthToken, setAuthToken } from "../src/api/client";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("AuthContext", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setAuthToken(null);
  });

  it("starts unauthenticated with no token", () => {
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.role).toBeNull();
  });

  it("login stores the token and role, and forwards it to the API client", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          access_token: "jwt-abc",
          token_type: "bearer",
          role: "operator",
          username: "operator",
        }),
      ),
    );
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await act(async () => {
      await result.current.login("operator", "operator123");
    });

    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(result.current.role).toBe("operator");
    expect(result.current.username).toBe("operator");
    expect(getAuthToken()).toBe("jwt-abc");
  });

  it("a failed login leaves the user unauthenticated and clears the client token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Invalid username or password" }, 401)),
    );
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await expect(
      act(async () => {
        await result.current.login("operator", "wrong-password");
      }),
    ).rejects.toThrow();

    expect(result.current.isAuthenticated).toBe(false);
    expect(getAuthToken()).toBeNull();
  });

  it("logout clears the token from both context and the API client", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          access_token: "jwt-abc",
          token_type: "bearer",
          role: "viewer",
          username: "viewer",
        }),
      ),
    );
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await act(async () => {
      await result.current.login("viewer", "viewer123");
    });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));

    act(() => result.current.logout());

    expect(result.current.isAuthenticated).toBe(false);
    expect(getAuthToken()).toBeNull();
  });
});
