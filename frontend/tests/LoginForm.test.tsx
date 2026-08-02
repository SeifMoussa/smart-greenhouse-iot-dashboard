import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../src/auth/AuthContext";
import { LoginForm } from "../src/components/LoginForm";
import { setAuthToken } from "../src/api/client";
import { renderWithQueryClient } from "./helpers";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("<LoginForm />", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setAuthToken(null);
  });

  it("submits username and password to the login endpoint", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      jsonResponse({
        access_token: "jwt-abc",
        token_type: "bearer",
        role: "operator",
        username: "operator",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderWithQueryClient(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "operator");
    await user.type(screen.getByLabelText(/password/i), "operator123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toContain("/api/auth/login");
    expect(JSON.parse(String((init as RequestInit).body))).toEqual({
      username: "operator",
      password: "operator123",
    });
  });

  it("shows an error message on invalid credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Invalid username or password" }, 401)),
    );

    renderWithQueryClient(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/username/i), "operator");
    await user.type(screen.getByLabelText(/password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid username or password/i);
  });
});
