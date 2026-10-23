import { describe, expect, it, vi } from "vitest";
import type { FinalReviewCopy } from "./use-final-review-copy";
import { copyBusy } from "./use-final-review-copy";

/** Gherkin: tests/features/copy-version-history-ae0506.feature. */

function copy(
  overrides: { dirty?: boolean; saving?: boolean; restoring?: boolean } = {},
): FinalReviewCopy {
  return {
    editor: {
      draft: { caption: "", linkedinPt: "", linkedinEn: "" },
      saved: { caption: "", linkedinPt: "", linkedinEn: "" },
      status: overrides.saving ? { kind: "saving" } : { kind: "idle" },
      canSave: true,
      isDirty: () => overrides.dirty === true,
      setText: vi.fn(),
      save: vi.fn(),
    },
    loadFailed: false,
    retry: vi.fn(),
    history: {
      versions: [],
      loading: false,
      status: overrides.restoring
        ? { kind: "restoring", versionNumber: 1 }
        : { kind: "idle" },
      hasMore: false,
      loadMore: vi.fn(),
    },
  };
}

describe("copyBusy (AE-0506)", () => {
  /** Scenario: Approve and send back wait while a restore runs */
  it("is busy while a text is unsaved, saving or restoring", () => {
    expect(copyBusy(copy())).toBe(false);
    expect(copyBusy(copy({ dirty: true }))).toBe(true);
    expect(copyBusy(copy({ saving: true }))).toBe(true);
    expect(copyBusy(copy({ restoring: true }))).toBe(true);
    expect(copyBusy({ ...copy({ restoring: true }), editor: null })).toBe(
      false,
    );
  });
});
