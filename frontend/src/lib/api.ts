export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("tai_token");
}

export function setToken(token: string) {
  localStorage.setItem("tai_token", token);
}

export function clearToken() {
  localStorage.removeItem("tai_token");
}

export async function api<T = unknown>(
  path: string,
  options: RequestInit & { json?: unknown } = {}
): Promise<T> {
  const { json, ...rest } = options;
  const headers: Record<string, string> = {
    ...(rest.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (json !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  if (res.status === 401 && typeof window !== "undefined") {
    clearToken();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  const data = res.headers.get("content-type")?.includes("application/json")
    ? await res.json()
    : await res.text();

  if (!res.ok) {
    const detail =
      typeof data === "object" && data && "detail" in (data as Record<string, unknown>)
        ? String((data as Record<string, unknown>).detail)
        : `Request failed (${res.status})`;
    throw new Error(detail);
  }
  return data as T;
}

export async function downloadFile(path: string, body: unknown, fallbackName: string) {
  const token = getToken();
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = "Export failed";
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {}
    throw new Error(detail);
  }
  const dispo = res.headers.get("content-disposition") || "";
  const match = dispo.match(/filename\*=UTF-8''(.+?)(?:;|$)/);
  const name = match ? decodeURIComponent(match[1]) : fallbackName;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
