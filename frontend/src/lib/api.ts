export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

/**
 * Wrapper around fetch that automatically adds the X-API-Key header
 * when NEXT_PUBLIC_API_KEY is set.
 */
export function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (API_KEY && !headers.has("x-api-key")) {
    headers.set("x-api-key", API_KEY);
  }
  return fetch(url, { ...init, headers });
}

/**
 * Append the API key as a query parameter for URLs that can't send custom headers
 * (e.g. <video src>, <img src>, <iframe src>).
 */
export function withApiKey(url: string): string {
  if (!API_KEY) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}api_key=${encodeURIComponent(API_KEY)}`;
}
