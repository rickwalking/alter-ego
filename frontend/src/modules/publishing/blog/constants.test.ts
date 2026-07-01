import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { BLOG_POST_STATUSES, toBlogPostStatus } from "./constants";

// Scenarios: see tests/features/blog-posts-listing-status-badge.feature
// ("Frontend status vocabulary matches the backend enum")

const BACKEND_ENUM_PATH = resolve(
  process.cwd(),
  "../backend/src/rag_backend/domain/constants/blog_post.py",
);

describe("toBlogPostStatus", () => {
  it("narrows every known status", () => {
    for (const status of BLOG_POST_STATUSES) {
      expect(toBlogPostStatus(status)).toBe(status);
    }
  });

  it("returns null for unknown values instead of passing them through", () => {
    expect(toBlogPostStatus("scheduled")).toBeNull();
    expect(toBlogPostStatus("")).toBeNull();
    expect(toBlogPostStatus("PUBLISHED")).toBeNull();
  });
});

describe("BlogPostStatus FE/BE contract (AE-0295 drift guard)", () => {
  // Skipped when the backend tree is absent (e.g. Stryker sandbox); the CI
  // gate runs from the full repo, so drift cannot land unnoticed.
  it.skipIf(!existsSync(BACKEND_ENUM_PATH))(
    "matches the backend BlogPostStatus enum values exactly",
    () => {
      const source = readFileSync(BACKEND_ENUM_PATH, "utf8");
      const classBody = source
        .split("class BlogPostStatus")[1]
        ?.split("\nclass ")[0];
      expect(classBody).toBeDefined();
      const backendValues = [...(classBody ?? "").matchAll(/= "([a-z_]+)"/g)]
        .map((m) => m[1])
        .sort();
      expect([...BLOG_POST_STATUSES].sort()).toEqual(backendValues);
    },
  );
});
