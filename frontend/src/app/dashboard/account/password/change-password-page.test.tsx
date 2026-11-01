/**
 * Gherkin: tests/features/change-own-password-ae0511.feature
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChangePasswordPage from "./page";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/dashboard/account/password",
}));

const ME_URL = "/api/auth/me";
const CHANGE_URL = "/api/auth/change-password";
const CURRENT = "current-pass-123";
const NEXT = "brand-new-pass-456";

interface Stub {
  forced: boolean;
  change: { status: number; body?: unknown };
}

function stubApi({ forced, change }: Stub): ReturnType<typeof vi.fn> {
  const user = {
    id: "u1",
    email: "editor@example.com",
    full_name: "Editor",
    role: "editor",
    must_change_password: forced,
  };
  const fetchMock = vi.fn((url: string) => {
    if (url === ME_URL) {
      return Promise.resolve(new Response(JSON.stringify(user)));
    }
    const body = change.body === undefined ? null : JSON.stringify(change.body);
    return Promise.resolve(new Response(body, { status: change.status }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderPage(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <ChangePasswordPage />
    </QueryClientProvider>,
  );
}

async function fillAndSubmit(values: {
  current: string;
  next: string;
  confirm: string;
}): Promise<void> {
  const user = userEvent.setup();
  await user.type(
    screen.getByLabelText(/current password|temporary password/i),
    values.current,
  );
  await user.type(screen.getByLabelText(/^new password/i), values.next);
  await user.type(
    screen.getByLabelText(/confirm the new password/i),
    values.confirm,
  );
  await user.click(screen.getByRole("button", { name: "Change password" }));
}

function changeCalls(fetchMock: ReturnType<typeof vi.fn>): unknown[][] {
  return fetchMock.mock.calls.filter(([url]) => url === CHANGE_URL);
}

beforeEach(() => {
  replace.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("change-password page", () => {
  // Scenario: A user changes their password from the dashboard
  it("changes the password, shows success and clears the form", async () => {
    const fetchMock = stubApi({ forced: false, change: { status: 204 } });
    renderPage();
    expect(
      await screen.findByText(
        "Enter your current password, then the new one twice.",
      ),
    ).toBeInTheDocument();

    await fillAndSubmit({ current: CURRENT, next: NEXT, confirm: NEXT });

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Password changed.",
    );
    expect(changeCalls(fetchMock)).toHaveLength(1);
    expect(screen.getByLabelText(/^new password/i)).toHaveValue("");
    expect(replace).not.toHaveBeenCalled();
  });

  // Scenario: A wrong current password shows a clear error
  it("says the current password is wrong on a coded 401", async () => {
    stubApi({
      forced: false,
      change: {
        status: 401,
        body: { detail: "x", code: "current_password_incorrect" },
      },
    });
    renderPage();

    await fillAndSubmit({
      current: "wrong-pass-0000",
      next: NEXT,
      confirm: NEXT,
    });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The current password is wrong.",
    );
    expect(replace).not.toHaveBeenCalled();
  });

  // Scenario: The form checks the new password before sending it
  it("refuses a mismatched confirmation without calling the API", async () => {
    const fetchMock = stubApi({ forced: false, change: { status: 204 } });
    renderPage();

    await fillAndSubmit({ current: CURRENT, next: NEXT, confirm: `${NEXT}x` });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The new password and its confirmation do not match.",
    );
    expect(changeCalls(fetchMock)).toHaveLength(0);
  });

  // Scenario: The form checks the new password before sending it
  it("refuses a short new password with the minimum in the message", async () => {
    stubApi({ forced: false, change: { status: 204 } });
    renderPage();

    await fillAndSubmit({ current: CURRENT, next: "short", confirm: "short" });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The new password needs at least 12 characters.",
    );
  });

  // Scenario: API refusals are translated
  it("translates a rate-limited change", async () => {
    stubApi({ forced: false, change: { status: 429 } });
    renderPage();

    await fillAndSubmit({ current: CURRENT, next: NEXT, confirm: NEXT });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Too many attempts. Wait a minute and try again.",
    );
  });

  // Scenario: The change-password page explains a forced change
  it("explains a forced change and labels the temporary password", async () => {
    stubApi({ forced: true, change: { status: 204 } });
    renderPage();

    expect(
      await screen.findByText(
        "An admin reset your password. Change the temporary password to keep using the app.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/temporary password/i)).toBeInTheDocument();
  });

  // Scenario: Changing the temporary password lets the user continue
  it("refreshes the session and goes to the dashboard after a forced change", async () => {
    const fetchMock = stubApi({ forced: true, change: { status: 204 } });
    renderPage();
    await screen.findByLabelText(/temporary password/i);

    await fillAndSubmit({ current: CURRENT, next: NEXT, confirm: NEXT });

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/dashboard/chat"),
    );
    const meCalls = fetchMock.mock.calls.filter(([url]) => url === ME_URL);
    expect(meCalls.length).toBeGreaterThanOrEqual(2);
  });
});
