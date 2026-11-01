/**
 * Gherkin: tests/features/change-own-password-ae0511.feature
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  passwordChangeErrorKey,
  passwordFormError,
  submitPasswordChange,
} from "./change-password";

const CURRENT = "current-pass-123";
const NEXT = "brand-new-pass-456";

function respond(status: number, body: unknown = null): void {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(body === null ? null : JSON.stringify(body), { status }),
      ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("passwordFormError", () => {
  // Scenario: The form checks the new password before sending it
  it.each([
    [{ current: CURRENT, next: "short", confirm: "short" }, "tooShort"],
    [{ current: CURRENT, next: NEXT, confirm: `${NEXT}x` }, "mismatch"],
    [{ current: NEXT, next: NEXT, confirm: NEXT }, "unchanged"],
  ])("refuses %o with %s", (values, key) => {
    expect(passwordFormError(values)).toBe(key);
  });

  // Scenario: A user changes their password from the dashboard
  it("accepts a long, confirmed, different new password", () => {
    expect(
      passwordFormError({ current: CURRENT, next: NEXT, confirm: NEXT }),
    ).toBeNull();
    expect(
      passwordFormError({
        current: CURRENT,
        next: "a".repeat(12),
        confirm: "a".repeat(12),
      }),
    ).toBeNull();
  });
});

describe("passwordChangeErrorKey", () => {
  // Scenario: API refusals are translated
  it.each([
    [401, "current_password_incorrect", "currentIncorrect"],
    [400, "password_unchanged", "unchanged"],
    [422, undefined, "tooShort"],
    [429, undefined, "tooMany"],
    [401, undefined, "failed"],
    [500, "other_code", "failed"],
  ])("maps %i %s to %s", (status, code, key) => {
    expect(passwordChangeErrorKey(status, code)).toBe(key);
  });
});

describe("submitPasswordChange", () => {
  // Scenario: A user changes their password from the dashboard
  it("posts the current and new password and resolves null on 204", async () => {
    respond(204);

    const result = await submitPasswordChange({
      current: CURRENT,
      next: NEXT,
      confirm: NEXT,
    });

    expect(result).toBeNull();
    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe("/api/auth/change-password");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(
      JSON.stringify({ current_password: CURRENT, new_password: NEXT }),
    );
  });

  // Scenario: A wrong current password shows a clear error
  it("returns the key of a coded refusal", async () => {
    respond(401, {
      detail: "Current password is incorrect",
      code: "current_password_incorrect",
    });

    expect(
      await submitPasswordChange({ current: "x", next: NEXT, confirm: NEXT }),
    ).toBe("currentIncorrect");
  });

  // Scenario: API refusals are translated
  it("reports a network failure as a failed change", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));

    expect(
      await submitPasswordChange({
        current: CURRENT,
        next: NEXT,
        confirm: NEXT,
      }),
    ).toBe("failed");
  });
});
