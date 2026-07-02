// Gherkin: tests/features/csp-hardening.feature (AE-0305)
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { buildContentSecurityPolicy, CSP_DEV_BACKEND_IMG_SOURCE } from "./csp";

const FRONTEND_ROOT = join(__dirname, "..", "..");
const REPO_ROOT = join(FRONTEND_ROOT, "..");
const CSP_HEADER_NAME = "Content-Security-Policy";

describe("buildContentSecurityPolicy (AE-0305)", () => {
  // Scenario: production policy excludes the dev backend image source
  it("excludes http://localhost:8000 from the production policy", () => {
    const prod = buildContentSecurityPolicy(true);

    expect(prod).not.toContain(CSP_DEV_BACKEND_IMG_SOURCE);
    expect(prod).toContain("img-src 'self' data: blob: https:;");
  });

  it("keeps every non-img-src directive identical across environments", () => {
    const stripImgSrc = (csp: string): string[] =>
      csp.split("; ").filter((directive) => !directive.startsWith("img-src"));

    expect(stripImgSrc(buildContentSecurityPolicy(true))).toEqual(
      stripImgSrc(buildContentSecurityPolicy(false)),
    );
  });

  // Scenario: development keeps local backend images working
  it("keeps the dev backend image source in non-production", () => {
    const dev = buildContentSecurityPolicy(false);

    expect(dev).toContain(
      `img-src 'self' data: blob: https: ${CSP_DEV_BACKEND_IMG_SOURCE}`,
    );
  });

  // Scenario: core protections never regress silently
  it.each([true, false])(
    "keeps core protections (isProduction=%s)",
    (isProduction) => {
      const csp = buildContentSecurityPolicy(isProduction);

      expect(csp).toContain("frame-ancestors 'none'");
      expect(csp).toContain("base-uri 'self'");
      expect(csp).toContain("form-action 'self'");
      expect(csp).toContain("default-src 'self'");
    },
  );
});

describe("single authoritative CSP layer (AE-0305 drift guard)", () => {
  // Scenario: the CSP has a single authoritative layer
  it("keeps nginx configs CSP-silent", () => {
    for (const config of ["nginx.conf", "nginx.conf.ssl"]) {
      const text = readFileSync(join(REPO_ROOT, "nginx", config), "utf-8");

      expect(text.toLowerCase()).not.toContain(CSP_HEADER_NAME.toLowerCase());
    }
  });

  it("keeps next.config.ts free of inline CSP literals (must use the builder)", () => {
    const text = readFileSync(join(FRONTEND_ROOT, "next.config.ts"), "utf-8");

    expect(text).toContain("buildContentSecurityPolicy");
    expect(text).not.toContain("img-src");
    expect(text).not.toContain(CSP_DEV_BACKEND_IMG_SOURCE + ";");
  });
});
