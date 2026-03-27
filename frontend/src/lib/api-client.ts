// Route all API calls through the Next.js rewrite proxy (/api/:path* → backend).
// Using an absolute backend URL here would bake the internal Docker hostname
// (e.g. http://backend:8000) into the browser bundle, making all fetches fail
// in the browser. The /api prefix is stripped by the rewrite rule before the
// request is forwarded to the backend.
const API_PREFIX = "/api";

export interface LimitError extends Error {
  type: "LIMIT";
  code: string;
  message: string;
  upgradeUrl: string;
}

export function isLimitError(err: unknown): err is LimitError {
  return (
    err instanceof Error &&
    (err as LimitError).type === "LIMIT"
  );
}

export async function apiClient<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    credentials: "include", // Always send cookies (httpOnly auth cookies)
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;

    // Structured plan-limit error from plan_gate.py
    if (
      response.status === 403 &&
      detail &&
      typeof detail === "object" &&
      detail.code
    ) {
      const err = new Error(detail.message ?? "Limite do plano atingido") as LimitError;
      err.type = "LIMIT";
      err.code = detail.code;
      err.upgradeUrl = detail.upgrade_url ?? "/planos";
      throw err;
    }

    // Generic error — FastAPI returns {"detail": "string"} for most errors
    const message =
      typeof detail === "string" ? detail : body.error ?? `HTTP ${response.status}`;
    throw new Error(message);
  }

  // 204 No Content — nothing to parse (e.g. DELETE responses)
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }
  return response.json();
}
