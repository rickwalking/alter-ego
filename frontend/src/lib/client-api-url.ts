/** Resolve browser API URLs, optionally bypassing the Next.js proxy in dev (RW-001). */

function getClientApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";
}

/** Prefix workflow API paths with NEXT_PUBLIC_API_URL when configured in the browser. */
export function resolveClientApiUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error("API path must start with /");
  }
  const baseUrl = getClientApiBaseUrl();
  if (!baseUrl || typeof window === "undefined") {
    return path;
  }
  return `${baseUrl}${path}`;
}
