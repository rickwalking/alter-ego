/**
 * Gherkin: tests/features/chat-errors-ui.feature
 */
import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

import { useRecheckSessionOnNotFound } from "./use-recheck-session";

describe("useRecheckSessionOnNotFound", () => {
  /** Scenario: A signed-in user whose session expired is told to sign in again */
  it("re-reads an authenticated endpoint when the conversation is not found", () => {
    const recheck = vi.fn();
    renderHook(() => useRecheckSessionOnNotFound("notFound", recheck));
    expect(recheck).toHaveBeenCalledOnce();
  });

  it.each([null, "offline", "generic"] as const)(
    "does nothing for %s",
    (error) => {
      const recheck = vi.fn();
      renderHook(() => useRecheckSessionOnNotFound(error, recheck));
      expect(recheck).not.toHaveBeenCalled();
    },
  );
});
