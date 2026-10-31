/**
 * Gherkin: tests/features/users-area-polish-ae0514.feature
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { useLogin } from "./use-login";

async function submitWith(response: Response | Error): Promise<string> {
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  if (response instanceof Error) {
    fetchSpy.mockRejectedValue(response);
  } else {
    fetchSpy.mockResolvedValue(response);
  }
  const { result } = renderHook(() => useLogin());
  await act(() =>
    result.current.handleSubmit({
      preventDefault: vi.fn(),
    } as unknown as React.SubmitEvent),
  );
  return result.current.error;
}

const SERVER_UNREACHABLE = "Couldn't reach the server. Try again in a moment.";

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useLogin failures", () => {
  // Scenario: A deactivated account sees a translated login message
  it("says the account is deactivated, never the API text", async () => {
    const error = await submitWith(
      jsonResponse(
        { detail: "User account is deactivated", code: "user_inactive" },
        401,
      ),
    );

    expect(error).toBe(
      "This account is deactivated. Ask an admin to reactivate it.",
    );
  });

  // Scenario: Wrong credentials keep the translated invalid-credentials message
  it.each([
    jsonResponse({ detail: "Some English text" }, 401),
    jsonResponse({ detail: "Invalid email or password" }, 401),
    jsonResponse({ detail: [{ loc: ["body", "email"] }] }, 422),
  ])("shows the translated invalid-credentials message", async (response) => {
    expect(await submitWith(response)).toBe("Invalid email or password");
  });

  // Scenario: A server failure says the server could not be reached
  it.each([
    jsonResponse({ detail: "Internal Server Error" }, 500),
    new Response("Bad Gateway", { status: 502 }),
    new Response("Service Unavailable", { status: 503 }),
  ])("says the server could not be reached on a 5xx", async (response) => {
    expect(await submitWith(response)).toBe(SERVER_UNREACHABLE);
  });

  // Scenario: A server failure says the server could not be reached
  it("says the server could not be reached when the request fails", async () => {
    expect(await submitWith(new TypeError("Failed to fetch"))).toBe(
      SERVER_UNREACHABLE,
    );
  });
});
