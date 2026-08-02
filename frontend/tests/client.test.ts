import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest, buildExportUrl, setAuthToken } from "../src/api/client";

describe("apiRequest", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setAuthToken(null);
  });

  it("attaches no Authorization header when no token is set", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () => new Response(JSON.stringify({}), { headers: { "content-type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/readings");

    const [, init] = fetchMock.mock.calls[0]!;
    expect((init as RequestInit).headers).not.toHaveProperty("Authorization");
  });

  it("attaches a Bearer Authorization header once a token is set", async () => {
    setAuthToken("abc123");
    const fetchMock = vi.fn<typeof fetch>(
      async () => new Response(JSON.stringify({}), { headers: { "content-type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/readings");

    const [, init] = fetchMock.mock.calls[0]!;
    expect((init as RequestInit).headers).toMatchObject({ Authorization: "Bearer abc123" });
  });

  it("clears the Authorization header after logout (setAuthToken(null))", async () => {
    setAuthToken("abc123");
    setAuthToken(null);
    const fetchMock = vi.fn<typeof fetch>(
      async () => new Response(JSON.stringify({}), { headers: { "content-type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/readings");

    const [, init] = fetchMock.mock.calls[0]!;
    expect((init as RequestInit).headers).not.toHaveProperty("Authorization");
  });

  it("parses JSON responses on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ status: "ok" }), {
            status: 200,
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    const result = await apiRequest<{ status: string }>("/api/health");
    expect(result).toEqual({ status: "ok" });
  });

  it("serializes body and sets content-type for POST", async () => {
    const fetchMock = vi.fn<typeof fetch>(
      async () =>
        new Response(JSON.stringify({ id: "fan", state: "on" }), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/api/actuators/fan/state", {
      method: "POST",
      body: { state: "on" },
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const call = fetchMock.mock.calls[0];
    expect(call).toBeDefined();
    const init = call![1] as RequestInit;
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ state: "on" }));
  });

  it("throws ApiError with detail when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "Invalid or missing API key" }), {
            status: 401,
            headers: { "content-type": "application/json" },
          }),
      ),
    );
    await expect(apiRequest("/api/readings", { method: "POST", body: {} })).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});

describe("buildExportUrl", () => {
  it("appends provided query parameters", () => {
    const url = buildExportUrl({
      from: "2026-01-01T00:00:00Z",
      to: "2026-01-02T00:00:00Z",
      type: "temperature",
    });
    expect(url).toContain("/api/export.csv?");
    expect(url).toContain("from=2026-01-01");
    expect(url).toContain("to=2026-01-02");
    expect(url).toContain("type=temperature");
  });

  it("omits parameters that are not provided", () => {
    const url = buildExportUrl({});
    expect(url).toMatch(/\/api\/export\.csv$/);
  });

  it("only includes the type parameter when only type is set", () => {
    const url = buildExportUrl({ type: "humidity" });
    expect(url).toContain("type=humidity");
    expect(url).not.toContain("from=");
    expect(url).not.toContain("to=");
  });
});
