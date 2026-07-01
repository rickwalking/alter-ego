import { afterEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_BACKEND_URL, PRODUCTION_BACKEND_URL } from "@/constants/api";
import { getBaseUrl } from "./server-fetch";

// Scenarios: see tests/features/public-blog-detail.feature
// ("Server-side base URL is overridable for production", AE-0297)

function simulateServerSide(): void {
  // `typeof window` evaluates to "undefined" when the binding holds undefined,
  // which is exactly the server-side branch getBaseUrl guards on.
  vi.stubGlobal("window", undefined);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("getBaseUrl server-side resolution (AE-0297)", () => {
  it("prefers the explicit API_BASE_URL override in production", () => {
    simulateServerSide();
    vi.stubEnv("API_BASE_URL", "http://droplet-internal:8000");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "/api");
    expect(getBaseUrl()).toBe("http://droplet-internal:8000");
  });

  it("falls back to the Docker-internal hostname for relative public URLs", () => {
    simulateServerSide();
    vi.stubEnv("API_BASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "/api");
    expect(getBaseUrl()).toBe(PRODUCTION_BACKEND_URL);
  });

  it("uses the public env URL when absolute", () => {
    simulateServerSide();
    vi.stubEnv("API_BASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    expect(getBaseUrl()).toBe("http://localhost:8000");
  });

  it("client-side ignores API_BASE_URL and uses the public env URL", () => {
    vi.stubEnv("API_BASE_URL", "http://droplet-internal:8000");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    expect(getBaseUrl()).toBe("http://localhost:8000");
  });

  it("defaults when no env is set server-side", () => {
    simulateServerSide();
    vi.stubEnv("API_BASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    expect(getBaseUrl()).toBe(DEFAULT_BACKEND_URL);
  });
});
