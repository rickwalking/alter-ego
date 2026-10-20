import { describe, expect, it } from "vitest";
import { editorErrorKey } from "./editor-error";

// Scenarios: tests/features/blog_editor_errors_ae0438.feature
// (code-specific copy for known backend details, kind-level fallback)

describe("editorErrorKey", () => {
  it("maps a known detail code to its code-specific message key", () => {
    expect(
      editorErrorKey({
        kind: "status_guard",
        detail: "self_review_not_allowed",
      }),
    ).toBe("errors.code.self_review");
  });

  it("maps the empty-version restore failure", () => {
    expect(
      editorErrorKey({ kind: "validation", detail: "blog_version_empty" }),
    ).toBe("errors.code.version_empty");
  });

  it("falls back to the kind-level key for unknown details", () => {
    expect(editorErrorKey({ kind: "validation", detail: "unknown_code" })).toBe(
      "errors.validation",
    );
    expect(editorErrorKey({ kind: "conflict", detail: null })).toBe(
      "errors.conflict",
    );
  });

  it("keeps version_conflict on the kind-level copy", () => {
    expect(
      editorErrorKey({ kind: "version_conflict", detail: "version_conflict" }),
    ).toBe("errors.version_conflict");
  });
});
