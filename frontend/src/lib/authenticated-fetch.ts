import { CONTENT_TYPES } from "@/constants/api";

/** Authenticated fetch helper for dashboard API calls. */
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", CONTENT_TYPES.JSON);
  }

  return fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });
}
