import { describe, it, expect, vi, afterEach } from "vitest";
import { resolveClientApiUrl } from "@/lib/client-api-url";

const ENV_KEY = "NEXT_PUBLIC_API_URL";
const PATH = "/api/carousels/id/workflow/state";

describe("resolveClientApiUrl without the env variable", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns the relative path in the browser when the variable is absent", () => {
    vi.stubEnv(ENV_KEY, undefined);
    expect(process.env[ENV_KEY]).toBeUndefined();
    expect(typeof window).toBe("object");
    expect(resolveClientApiUrl(PATH)).toBe(PATH);
  });
});
