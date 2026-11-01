/**
 * Gherkin: tests/features/last-active-admin-guard-ae0585.feature
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import UsersPage from "./page";

const ADMIN = {
  id: "a1",
  email: "admin@example.com",
  full_name: "Only Admin",
  role: "admin",
  is_active: true,
  created_at: "2026-10-01T00:00:00Z",
};
const OTHER_ADMIN = {
  ...ADMIN,
  id: "a2",
  email: "other@example.com",
  full_name: "Other Admin",
};
const EDITOR = {
  ...ADMIN,
  id: "e1",
  email: "editor@example.com",
  full_name: "Some Editor",
  role: "editor",
};

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** The role select and active checkbox of the open edit dialog. */
function controls(): { role: HTMLElement; active: HTMLElement } {
  const dialog = within(screen.getByRole("dialog"));
  return {
    role: dialog.getByLabelText("Role"),
    active: dialog.getByLabelText("Active"),
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("users page last-active-admin lock", () => {
  // Scenario: The controls stay enabled when another admin is active
  it("counts the full list, not the filtered rows", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ items: [ADMIN, OTHER_ADMIN, EDITOR], total: 3 }, 200),
        ),
    );
    const user = userEvent.setup();
    render(<UsersPage />);
    await waitFor(() =>
      expect(screen.getByText("Only Admin")).toBeInTheDocument(),
    );

    await user.type(screen.getByLabelText("Search"), "Only");
    await waitFor(() =>
      expect(screen.queryByText("Other Admin")).not.toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(controls().role).toBeEnabled();
    expect(controls().active).toBeEnabled();
  });

  // Scenario: Inactive admins do not count as active admins
  it("locks the active admin when the other admin is inactive", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            items: [ADMIN, { ...OTHER_ADMIN, is_active: false }],
            total: 2,
          },
          200,
        ),
      ),
    );
    const user = userEvent.setup();
    render(<UsersPage />);
    await waitFor(() =>
      expect(screen.getByText("Only Admin")).toBeInTheDocument(),
    );

    const adminRow = screen.getByText("Only Admin").closest("tr");
    await user.click(
      within(adminRow as HTMLElement).getByRole("button", { name: "Edit" }),
    );

    expect(controls().role).toBeDisabled();
    expect(controls().active).toBeDisabled();
  });
});
