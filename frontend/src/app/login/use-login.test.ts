import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { useLogin } from "./use-login";

function openLogin(search: string): void {
  window.history.replaceState(null, "", `/login${search}`);
}

afterEach(() => {
  openLogin("");
  vi.restoreAllMocks();
});

describe("useLogin notices", () => {
  // Scenario: A failed sign-in without JavaScript returns an error code only
  // Scenario: A rate-limited sign-in without JavaScript says to wait
  it.each([
    ["?error=invalid_credentials", "Invalid email or password"],
    [
      "?error=too_many_attempts",
      "Too many sign-in attempts. Wait a minute and try again.",
    ],
    ["?error=session_expired", "Your session expired. Please sign in again."],
    ["?error=other", ""],
  ])("shows the notice for %s", async (search, notice) => {
    openLogin(search);
    const { result } = renderHook(() => useLogin());

    await waitFor(() => expect(result.current.error).toBe(notice));
  });

  // Scenario: A rate-limited sign-in without JavaScript says to wait
  it("says to wait when the API rate-limits a sign-in", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Rate limit exceeded" }), {
        status: 429,
      }),
    );
    const { result } = renderHook(() => useLogin());

    await act(() =>
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      } as unknown as React.SubmitEvent),
    );

    expect(result.current.error).toBe(
      "Too many sign-in attempts. Wait a minute and try again.",
    );
  });
});
