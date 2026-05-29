import { describe, it, expect, vi, afterEach } from "vitest";
import { resolveClientApiUrl } from "@/lib/client-api-url";

describe("resolveClientApiUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns relative paths when NEXT_PUBLIC_API_URL is unset", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    expect(resolveClientApiUrl("/api/carousels/id/workflow/resume")).toBe(
      "/api/carousels/id/workflow/resume",
    );
  });

  it("prefixes workflow paths with NEXT_PUBLIC_API_URL in the browser", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    expect(resolveClientApiUrl("/api/carousels/id/workflow/state")).toBe(
      "http://localhost:8000/api/carousels/id/workflow/state",
    );
  });

  it("strips trailing slash from NEXT_PUBLIC_API_URL", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000/");
    expect(resolveClientApiUrl("/api/carousels/id/workflow/stream")).toBe(
      "http://localhost:8000/api/carousels/id/workflow/stream",
    );
  });

  it("throws when the API path does not start with a slash", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    expect(() => resolveClientApiUrl("api/carousels/id/workflow/state")).toThrow(
      "API path must start with /",
    );
  });

  it("returns relative paths during SSR even when NEXT_PUBLIC_API_URL is set", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    const originalWindow = globalThis.window;
    // @ts-expect-error — simulate SSR where window is unavailable.
    delete globalThis.window;

    expect(resolveClientApiUrl("/api/carousels/id/workflow/resume")).toBe(
      "/api/carousels/id/workflow/resume",
    );

    globalThis.window = originalWindow;
  });
});
