/**
 * Lightweight typed fetch wrapper. We deliberately use the platform `fetch`
 * rather than pulling in a heavyweight HTTP library — the API surface is
 * small and well-typed.
 */

const FALLBACK_API = "http://localhost:8000";

function getApiBaseUrl(): string {
  const url = import.meta.env.VITE_API_BASE_URL?.trim();
  return url && url.length > 0 ? url : FALLBACK_API;
}

// Held in memory only — never localStorage/sessionStorage, so it can't be
// read by an XSS payload that outlives the page, and it's gone on refresh.
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const base = getApiBaseUrl().replace(/\/+$/, "");
  const url = `${base}${path}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    ...(options.headers ?? {}),
  };
  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(url, {
    method: options.method ?? "GET",
    headers,
    body,
    signal: options.signal,
  });

  if (!response.ok) {
    let parsed: unknown;
    try {
      parsed = await response.json();
    } catch {
      parsed = undefined;
    }
    const detail =
      typeof parsed === "object" &&
      parsed !== null &&
      "detail" in parsed &&
      typeof (parsed as { detail: unknown }).detail === "string"
        ? (parsed as { detail: string }).detail
        : `Request failed: ${response.status}`;
    throw new ApiError(response.status, detail, parsed);
  }

  // 204 No Content / empty body safety:
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

export function buildExportUrl(params: { from?: string; to?: string; type?: string }): string {
  const base = getApiBaseUrl().replace(/\/+$/, "");
  const search = new URLSearchParams();
  if (params.from) search.set("from", params.from);
  if (params.to) search.set("to", params.to);
  if (params.type) search.set("type", params.type);
  const qs = search.toString();
  return `${base}/api/export.csv${qs ? `?${qs}` : ""}`;
}

/**
 * Download the CSV export with the auth header attached.
 *
 * This can't be a plain `<a href>` anymore now that the endpoint requires
 * a Bearer token — browsers don't attach custom headers to a normal
 * navigation, so instead we fetch it, then hand the browser a blob URL
 * to save. Filename is read from the server's Content-Disposition header.
 */
export async function downloadExportCsv(params: {
  from?: string;
  to?: string;
  type?: string;
}): Promise<void> {
  const url = buildExportUrl(params);
  const headers: Record<string, string> = authToken ? { Authorization: `Bearer ${authToken}` } : {};
  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new ApiError(response.status, `Export failed: ${response.status}`);
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? "greenhouse-readings.csv";

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
